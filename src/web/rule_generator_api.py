"""智能规则生成API。"""

import json
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import jieba.analyse
import jieba

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from src.config import settings
from src.logger import logger


router = APIRouter()


class RuleGenerationRequest(BaseModel):
    """规则生成请求。"""
    event_id: str
    content: str
    detection_type: str
    matched_text: Optional[str] = None
    existing_rule_id: Optional[str] = None
    severity: Optional[str] = "medium"


class GeneratedRule(BaseModel):
    """生成的规则。"""
    id: str
    name: str
    description: str
    detection_type: str
    severity: str
    patterns: List[str]
    keywords: List[str]
    enabled: bool = True
    block: bool = True
    priority: int = 100
    categories: List[str]
    confidence_score: float
    explanation: str
    similar_rules: List[str] = []


class RuleGenerationResponse(BaseModel):
    """规则生成响应。"""
    success: bool
    generated_rule: Optional[GeneratedRule] = None
    suggestions: List[str] = []
    warnings: List[str] = []
    conflicts: List[str] = []


class RuleGeneratorService:
    """规则生成服务。"""
    
    def __init__(self):
        self.load_existing_rules()
        # 初始化jieba分词
        jieba.initialize()
    
    def load_existing_rules(self):
        """加载现有规则。"""
        self.existing_rules = {}
        
        # 加载各类规则文件
        rule_files = [
            'rules/harmful_content.json',
            'rules/sensitive_info.json', 
            'rules/prompt_injection.json',
            'rules/jailbreak.json'
        ]
        
        for rule_file in rule_files:
            try:
                with open(rule_file, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                    for rule in rules:
                        self.existing_rules[rule['id']] = rule
            except FileNotFoundError:
                logger.warning(f"规则文件不存在: {rule_file}")
            except Exception as e:
                logger.error(f"加载规则文件失败 {rule_file}: {e}")
    
    def extract_keywords(self, content: str, matched_text: str = None) -> List[str]:
        """从内容中提取关键词。"""
        keywords = []
        
        # 使用jieba提取关键词
        try:
            jieba_keywords = jieba.analyse.extract_tags(content, topK=10, withWeight=False)
            keywords.extend(jieba_keywords)
        except Exception as e:
            logger.warning(f"jieba关键词提取失败: {e}")
        
        # 如果有匹配文本，直接提取其中的关键词
        if matched_text:
            # 去掉标点符号，提取纯文本关键词
            clean_text = re.sub(r'[^\w\s]', ' ', matched_text)
            words = clean_text.split()
            keywords.extend([w for w in words if len(w) > 1])
        
        # 去重并过滤短词
        keywords = list(set([k for k in keywords if len(k) >= 2]))
        
        return keywords[:8]  # 限制关键词数量
    
    def generate_patterns(self, content: str, matched_text: str, detection_type: str) -> List[str]:
        """生成正则表达式模式。"""
        patterns = []
        
        if not content:
            return patterns
        
        # 如果是监控规则，生成更广泛的监控模式
        if detection_type == "content_monitoring":
            # 基于内容生成宽泛的监控模式
            keywords = jieba.analyse.extract_tags(content, topK=5, withWeight=False)
            if keywords:
                # 生成包含主要关键词的模式
                main_keywords = keywords[:3]  # 取前3个关键词
                if len(main_keywords) >= 2:
                    pattern = f"(?i).*{re.escape(main_keywords[0])}.*{re.escape(main_keywords[1])}.*"
                    patterns.append(pattern)
                
                # 为每个主要关键词创建简单模式
                for keyword in main_keywords:
                    if len(keyword) >= 2:
                        patterns.append(f"(?i){re.escape(keyword)}")
            
            return patterns[:3]  # 限制模式数量，避免过度监控
        
        # 对于从已允许事件生成阻止规则，使用更精确的模式
        if detection_type in ["harmful_content", "sensitive_info", "prompt_injection", "jailbreak"]:
            # 基于内容生成精确的阻止模式
            keywords = jieba.analyse.extract_tags(content, topK=5, withWeight=False)
            if keywords:
                # 生成包含关键词的精确模式
                for keyword in keywords[:3]:
                    if len(keyword) >= 2:
                        patterns.append(f"(?i)(?:\\\\b{re.escape(keyword)}\\\\b)")
                
                # 如果有足够的关键词，生成组合模式
                if len(keywords) >= 2:
                    pattern = f"(?i)(?:.*{re.escape(keywords[0])}.*{re.escape(keywords[1])}.*)"
                    patterns.append(pattern)
            
            return patterns[:4]  # 阻止规则可以有更多模式
            
        # 其他检测类型的现有逻辑
        if not matched_text:
            return patterns
        
        # 基础模式：直接匹配
        escaped_text = re.escape(matched_text)
        patterns.append(f"(?i){escaped_text}")
        
        # 根据检测类型生成特定模式
        if detection_type == "harmful_content":
            patterns.extend(self._generate_harmful_content_patterns(matched_text))
        elif detection_type == "sensitive_info":
            patterns.extend(self._generate_sensitive_info_patterns(matched_text))
        elif detection_type == "prompt_injection":
            patterns.extend(self._generate_prompt_injection_patterns(matched_text))
        elif detection_type == "jailbreak":
            patterns.extend(self._generate_jailbreak_patterns(matched_text))
        
        return patterns[:5]  # 限制模式数量
    
    def _generate_harmful_content_patterns(self, matched_text: str) -> List[str]:
        """生成有害内容的模式。"""
        patterns = []
        
        # 提取动词和名词组合
        violence_verbs = ["制作", "制造", "建造", "生产", "创建", "制备"]
        violence_objects = ["炸弹", "武器", "刀具", "毒药", "爆炸物"]
        
        for verb in violence_verbs:
            if verb in matched_text:
                for obj in violence_objects:
                    if obj in matched_text:
                        pattern = f"(?i)(?:{verb}|make|create)[\\s]*(?:{obj}|weapon|bomb)"
                        patterns.append(pattern)
        
        return patterns
    
    def _generate_sensitive_info_patterns(self, matched_text: str) -> List[str]:
        """生成敏感信息的模式。"""
        patterns = []
        
        # 检查是否包含常见敏感信息模式
        if re.search(r'\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}', matched_text):
            patterns.append(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b')
        
        if re.search(r'\d{3}-?\d{2}-?\d{4}', matched_text):
            patterns.append(r'\b\d{3}-?\d{2}-?\d{4}\b')
        
        return patterns
    
    def _generate_prompt_injection_patterns(self, matched_text: str) -> List[str]:
        """生成提示注入的模式。"""
        patterns = []
        
        injection_phrases = ["忽略", "ignore", "forget", "代替", "instead", "角色扮演"]
        for phrase in injection_phrases:
            if phrase in matched_text.lower():
                patterns.append(f"(?i){re.escape(phrase)}")
        
        return patterns
    
    def _generate_jailbreak_patterns(self, matched_text: str) -> List[str]:
        """生成越狱尝试的模式。"""
        patterns = []
        
        jailbreak_phrases = ["假设", "imagine", "pretend", "你现在是", "扮演"]
        for phrase in jailbreak_phrases:
            if phrase in matched_text.lower():
                patterns.append(f"(?i){re.escape(phrase)}")
        
        return patterns
    
    def check_rule_conflicts(self, patterns: List[str], keywords: List[str]) -> List[str]:
        """检查规则冲突。"""
        conflicts = []
        
        for rule_id, rule in self.existing_rules.items():
            # 检查模式重叠
            for pattern in patterns:
                for existing_pattern in rule.get('patterns', []):
                    if pattern == existing_pattern:
                        conflicts.append(f"模式与规则 {rule_id} 重复: {pattern}")
            
            # 检查关键词重叠
            existing_keywords = rule.get('keywords', [])
            overlap = set(keywords) & set(existing_keywords)
            if len(overlap) >= 2:  # 如果有2个或以上关键词重叠
                conflicts.append(f"关键词与规则 {rule_id} 重叠: {', '.join(overlap)}")
        
        return conflicts
    
    def calculate_confidence_score(self, patterns: List[str], keywords: List[str], 
                                 matched_text: str, detection_type: str) -> float:
        """计算置信度分数。"""
        score = 0.0
        
        # 基础分数
        score += 0.3
        
        # 模式质量评分
        if patterns:
            score += 0.2
        if len(patterns) > 1:
            score += 0.1
        
        # 关键词质量评分
        if keywords:
            score += 0.2
        if len(keywords) >= 3:
            score += 0.1
        
        # 匹配文本清晰度评分
        if matched_text and len(matched_text.strip()) >= 3:
            score += 0.1
        
        return min(score, 1.0)
    
    def generate_rule_name(self, detection_type: str, keywords: List[str]) -> str:
        """生成规则名称。"""
        type_names = {
            "harmful_content": "有害内容",
            "sensitive_info": "敏感信息", 
            "prompt_injection": "提示注入",
            "jailbreak": "越狱尝试",
            "monitoring_rule": "内容监控",
            "content_monitoring": "内容监控"
        }
        
        type_name = type_names.get(detection_type, "未知类型")
        
        if keywords:
            key_phrase = "_".join(keywords[:2])
            return f"自动生成_{type_name}_{key_phrase}"
        else:
            return f"自动生成_{type_name}_{datetime.now().strftime('%m%d_%H%M')}"
    
    def generate_rule_from_event(self, request: RuleGenerationRequest) -> RuleGenerationResponse:
        """从事件生成规则。"""
        try:
            # 提取关键词
            keywords = self.extract_keywords(request.content, request.matched_text)
            
            # 生成模式
            patterns = self.generate_patterns(
                request.content, 
                request.matched_text or "", 
                request.detection_type
            )
            
            # 检查冲突
            conflicts = self.check_rule_conflicts(patterns, keywords)
            
            # 计算置信度
            confidence_score = self.calculate_confidence_score(
                patterns, keywords, request.matched_text or "", request.detection_type
            )
            
            # 生成规则ID
            rule_id = f"ag-{request.detection_type[:2]}-{str(uuid.uuid4())[:8]}"
            
            # 根据检测类型确定规则属性
            is_monitoring_rule = request.detection_type == "content_monitoring"
            is_blocking_rule = request.detection_type in ["harmful_content", "sensitive_info", "prompt_injection", "jailbreak"]
            
            # 对于从已允许事件生成阻止规则的情况，调整严重性
            if is_blocking_rule:
                default_severity = "high"  # 从已允许事件生成的阻止规则通常较严重
            elif is_monitoring_rule:
                default_severity = "low"   # 监控规则通常优先级较低
            else:
                default_severity = "medium"
                
            rule_severity = request.severity or default_severity
            
            # detection_type 直接使用请求中的类型，无需转换
            actual_detection_type = request.detection_type
            
            # 生成规则名称
            rule_name = self.generate_rule_name(actual_detection_type, keywords)
            
            # 创建生成的规则
            generated_rule = GeneratedRule(
                id=rule_id,
                name=rule_name,
                description=f"基于已允许事件 {request.event_id} 自动生成的{'监控' if is_monitoring_rule else '阻止'}规则",
                detection_type=actual_detection_type,
                severity=rule_severity,
                patterns=patterns,
                keywords=keywords,
                categories=[actual_detection_type, "auto_generated"],
                confidence_score=confidence_score,
                explanation=f"该规则基于已允许通过的内容 '{request.matched_text or request.content[:50]}' 自动生成，用于{'监控类似内容的出现' if is_monitoring_rule else '阻止类似的危险内容'}，包含 {len(patterns)} 个模式和 {len(keywords)} 个关键词。",
                similar_rules=[rule_id for rule_id in self.existing_rules.keys() if self.existing_rules[rule_id].get('detection_type') == actual_detection_type][:3],
                # 添加监控规则的默认配置
                enabled=True,
                block=not is_monitoring_rule,  # 监控规则不阻止，阻止规则阻止
                priority=50 if is_monitoring_rule else 100  # 监控规则优先级较低
            )
            
            # 生成建议
            suggestions = []
            if is_monitoring_rule:
                suggestions.append("这是一个内容监控规则，用于记录和观察类似内容的出现频率")
                suggestions.append("监控规则不会阻止内容通过，仅用于统计分析")
                if confidence_score < 0.7:
                    suggestions.append("建议调整关键词和模式以准确监控目标内容")
            elif is_blocking_rule:
                suggestions.append("这是从已允许内容生成的阻止规则，用于防止类似的潜在危险内容")
                suggestions.append("请仔细检查规则是否会误阻正常内容")
                if confidence_score < 0.7:
                    suggestions.append("建议手动检查并调整规则，置信度较低")
                if len(keywords) < 2:
                    suggestions.append("建议添加更多关键词以提高准确性")
                if not patterns:
                    suggestions.append("建议添加正则表达式模式以精确匹配")
            else:
                if confidence_score < 0.7:
                    suggestions.append("建议手动检查并调整规则，置信度较低")
                if len(keywords) < 2:
                    suggestions.append("建议添加更多关键词以提高准确性")
            
            # 生成警告
            warnings = []
            if conflicts:
                warnings.extend(conflicts)
            if confidence_score < 0.5:
                warnings.append("置信度过低，建议仔细审查规则")
            if is_monitoring_rule and len(patterns) > 3:
                warnings.append("监控规则模式过多，可能产生过多的监控记录")
            
            return RuleGenerationResponse(
                success=True,
                generated_rule=generated_rule,
                suggestions=suggestions,
                warnings=warnings,
                conflicts=conflicts
            )
            
        except Exception as e:
            logger.error(f"生成规则失败: {e}")
            return RuleGenerationResponse(
                success=False,
                suggestions=[],
                warnings=[f"规则生成失败: {str(e)}"],
                conflicts=[]
            )


# 全局服务实例
rule_generator = RuleGeneratorService()


@router.post("/api/v1/rules/generate", response_model=RuleGenerationResponse)
async def generate_rule_from_event(request: RuleGenerationRequest):
    """从安全事件生成规则。
    
    Args:
        request: 规则生成请求
        
    Returns:
        生成的规则和相关信息
    """
    try:
        return rule_generator.generate_rule_from_event(request)
    except Exception as e:
        logger.error(f"API调用失败: {e}")
        raise HTTPException(status_code=500, detail=f"规则生成失败: {str(e)}")


@router.post("/api/v1/rules/save-generated")
async def save_generated_rule(rule_data: Dict[str, Any] = Body(...)):
    """保存自动生成的规则。
    
    Args:
        rule_data: 规则数据
        
    Returns:
        保存结果
    """
    try:
        detection_type = rule_data.get('detection_type')
        if not detection_type:
            raise HTTPException(status_code=400, detail="缺少 detection_type")
        
        # 确定规则文件
        file_mapping = {
            'harmful_content': 'rules/harmful_content.json',
            'sensitive_info': 'rules/sensitive_info.json',
            'prompt_injection': 'rules/prompt_injection.json', 
            'jailbreak': 'rules/jailbreak.json',
            'content_monitoring': 'rules/harmful_content.json'  # 监控规则也保存到harmful_content文件中
        }
        
        rule_file = file_mapping.get(detection_type)
        if not rule_file:
            raise HTTPException(status_code=400, detail=f"不支持的检测类型: {detection_type}")
        
        # 读取现有规则
        try:
            with open(rule_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
        except FileNotFoundError:
            rules = []
        
        # 添加新规则
        is_monitoring = rule_data['detection_type'] == 'content_monitoring'
        new_rule = {
            "id": rule_data['id'],
            "name": rule_data['name'],
            "description": rule_data['description'],
            "detection_type": rule_data['detection_type'],
            "severity": rule_data['severity'],
            "patterns": rule_data['patterns'],
            "keywords": rule_data['keywords'],
            "enabled": rule_data.get('enabled', True),
            "block": rule_data.get('block', not is_monitoring),  # 监控规则默认不阻止
            "priority": rule_data.get('priority', 50 if is_monitoring else 100),  # 监控规则优先级较低
            "categories": rule_data.get('categories', []),
            "created_at": datetime.now().isoformat(),
            "created_by": "auto_generator"
        }
        
        # 检查是否已存在相同ID的规则
        existing_index = None
        for i, rule in enumerate(rules):
            if rule['id'] == new_rule['id']:
                existing_index = i
                break
        
        if existing_index is not None:
            # 更新现有规则
            rules[existing_index] = new_rule
        else:
            # 添加新规则
            rules.append(new_rule)
        
        # 保存规则文件
        with open(rule_file, 'w', encoding='utf-8') as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)
        
        logger.info(f"成功保存自动生成的规则: {new_rule['id']}")
        
        # 重新加载规则到服务实例
        rule_generator.load_existing_rules()
        
        return {
            "success": True,
            "message": f"规则 {new_rule['id']} 保存成功",
            "rule_id": new_rule['id']
        }
        
    except Exception as e:
        logger.error(f"保存规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存规则失败: {str(e)}")


@router.get("/api/v1/rules/templates")
async def get_rule_templates():
    """获取规则模板。
    
    Returns:
        规则模板列表
    """
    templates = {
        "harmful_content": {
            "name": "有害内容检测",
            "patterns": [
                "(?i)(?:制作|制造|make|create)[\\s]*(?:武器|weapon|bomb)",
                "(?i)(?:伤害|hurt|harm)[\\s]*(?:他人|others|people)"
            ],
            "keywords": ["武器", "伤害", "暴力"],
            "severity": "high"
        },
        "sensitive_info": {
            "name": "敏感信息检测",
            "patterns": [
                "\\b\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}\\b",
                "\\b\\d{3}-?\\d{2}-?\\d{4}\\b"
            ],
            "keywords": ["身份证", "银行卡", "密码"],
            "severity": "medium"
        },
        "prompt_injection": {
            "name": "提示注入检测", 
            "patterns": [
                "(?i)(?:ignore|忽略)[\\s]*(?:previous|之前|以上)",
                "(?i)(?:forget|忘记)[\\s]*(?:instructions|指令)"
            ],
            "keywords": ["忽略", "指令", "角色"],
            "severity": "high"
        },
        "jailbreak": {
            "name": "越狱尝试检测",
            "patterns": [
                "(?i)(?:pretend|假设|imagine)[\\s]*(?:you are|你是)",
                "(?i)(?:role.?play|角色扮演)"
            ],
            "keywords": ["假设", "扮演", "角色"],
            "severity": "high" 
        }
    }
    
    return {"success": True, "templates": templates}