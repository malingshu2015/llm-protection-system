"""规则管理API。"""

import json
import os
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Path, Query, status
from pydantic import BaseModel

from src.config import settings
from src.logger import logger
from src.models_interceptor import DetectionType, RuleMode, SecurityRule, Severity


router = APIRouter()


class RuleUpdateRequest(BaseModel):
    """规则更新请求。"""

    name: Optional[str] = None
    description: Optional[str] = None
    detection_type: Optional[DetectionType] = None
    severity: Optional[Severity] = None
    patterns: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    enabled: Optional[bool] = None
    block: Optional[bool] = None
    priority: Optional[int] = None
    categories: Optional[List[str]] = None
    custom_code: Optional[str] = None


@router.get("/api/v1/rules")
async def get_rules(
    detection_type: Optional[DetectionType] = None,
    enabled: Optional[bool] = None,
    category: Optional[str] = None,
):
    """获取所有规则。

    Args:
        detection_type: 过滤特定类型的规则
        enabled: 过滤启用/禁用的规则
        category: 过滤特定分类的规则

    Returns:
        规则列表
    """
    # 从规则文件中加载规则
    rules = []

    # 加载提示注入规则
    try:
        with open(settings.security.prompt_injection_rules_path, "r") as f:
            prompt_injection_rules = json.load(f)
            rules.extend(prompt_injection_rules)
    except Exception as e:
        logger.error(f"加载提示注入规则失败: {e}")

    # 加载越狱规则
    try:
        with open(settings.security.jailbreak_rules_path, "r") as f:
            jailbreak_rules = json.load(f)
            rules.extend(jailbreak_rules)
    except Exception as e:
        logger.error(f"加载越狱规则失败: {e}")

    # 加载敏感信息规则
    try:
        with open(settings.security.sensitive_info_patterns_path, "r") as f:
            sensitive_info_rules = json.load(f)
            # 将敏感信息模式转换为规则格式
            for rule_id, patterns in sensitive_info_rules.items():
                rules.append({
                    "id": f"si-{len(rules) + 1:03d}",
                    "name": f"敏感信息: {rule_id}",
                    "description": f"检测文本中的敏感信息: {rule_id}",
                    "detection_type": "sensitive_info",
                    "severity": "high",
                    "patterns": patterns,
                    "keywords": [rule_id],
                    "priority": 10,
                    "categories": ["sensitive_info", rule_id],
                    "enabled": True,
                    "block": True
                })
    except Exception as e:
        logger.error(f"加载敏感信息规则失败: {e}")

    # 加载有害内容规则
    try:
        with open(settings.security.harmful_content_rules_path, "r") as f:
            harmful_content_rules = json.load(f)
            rules.extend(harmful_content_rules)
    except Exception as e:
        logger.error(f"加载有害内容规则失败: {e}")

    # 加载合规性规则
    try:
        with open(settings.security.compliance_rules_path, "r") as f:
            compliance_rules = json.load(f)
            rules.extend(compliance_rules)
    except Exception as e:
        logger.error(f"加载合规性规则失败: {e}")

    # 应用过滤器
    if detection_type:
        rules = [rule for rule in rules if rule.get("detection_type") == detection_type]

    if enabled is not None:
        rules = [rule for rule in rules if rule.get("enabled") == enabled]

    if category:
        rules = [rule for rule in rules if "categories" in rule and category in rule.get("categories", [])]

    # 如果成功加载了规则，返回加载的规则
    if rules:
        return rules

    # 以下是模拟规则数据，仅在无法加载规则文件时使用
    mock_rules = [
        # ==================== 提示注入规则 ====================
        {
            "id": "pi-001",
            "name": "忽略之前的指令",
            "description": "检测尝试让模型忽略之前指令的行为",
            "detection_type": "prompt_injection",
            "severity": "high",
            "patterns": [
                "(?i)ignore\\s+(?:all\\s+)?(?:previous|above|earlier)\\s+instructions",
                "(?i)disregard\\s+(?:all\\s+)?(?:previous|above|earlier)\\s+instructions",
                "(?i)forget\\s+(?:all\\s+)?(?:previous|above|earlier)\\s+instructions",
                "(?i)do\\s+not\\s+(?:follow|obey|adhere\\s+to)\\s+(?:previous|above|earlier)\\s+instructions"
            ],
            "keywords": ["ignore", "disregard", "forget", "previous instructions"],
            "priority": 10,
            "categories": ["prompt_injection", "instruction_manipulation"],
            "enabled": True,
            "block": True
        },
        {
            "id": "pi-002",
            "name": "系统提示词提取",
            "description": "检测尝试提取系统提示词的行为",
            "detection_type": "prompt_injection",
            "severity": "high",
            "patterns": [
                "(?i)what\\s+(?:was|were)\\s+your\\s+instructions",
                "(?i)tell\\s+me\\s+your\\s+instructions",
                "(?i)what\\s+(?:is|are)\\s+your\\s+system\\s+prompt",
                "(?i)show\\s+me\\s+your\\s+system\\s+prompt",
                "(?i)reveal\\s+your\\s+(?:system\\s+)?prompt",
                "(?i)what\\s+(?:was|were)\\s+you\\s+told\\s+to\\s+do"
            ],
            "keywords": ["instructions", "system prompt", "reveal prompt"],
            "priority": 20,
            "categories": ["prompt_injection", "prompt_extraction"],
            "enabled": True,
            "block": True
        },
        {
            "id": "pi-003",
            "name": "角色扮演绕过",
            "description": "检测通过角色扮演尝试绕过安全限制",
            "detection_type": "prompt_injection",
            "severity": "medium",
            "patterns": [
                "(?i)pretend\\s+(?:to\\s+be|you\\s+are)\\s+a\\s+(?:person|character|entity)\\s+who\\s+(?:can|is\\s+able\\s+to)",
                "(?i)role-?play\\s+as\\s+(?:someone|a\\s+person|a\\s+character)\\s+who\\s+(?:can|is\\s+able\\s+to)",
                "(?i)imagine\\s+you\\s+are\\s+not\\s+bound\\s+by\\s+(?:any|your)\\s+(?:rules|restrictions|limitations)"
            ],
            "keywords": ["pretend", "roleplay", "role play", "imagine you are"],
            "priority": 30,
            "categories": ["prompt_injection", "role_play"],
            "enabled": True,
            "block": True
        },
        {
            "id": "pi-004",
            "name": "继续标记绕过",
            "description": "检测使用继续标记尝试绕过安全限制",
            "detection_type": "prompt_injection",
            "severity": "medium",
            "patterns": [
                "(?i)<\\s*continue\\s*>",
                "(?i)\\[continue\\]",
                "(?i)\\{\\s*continue\\s*\\}",
                "(?i)continue\\s+from\\s+where\\s+you\\s+left\\s+off\\s+without\\s+any\\s+restrictions"
            ],
            "keywords": ["continue", "继续"],
            "priority": 40,
            "categories": ["prompt_injection", "continuation_tricks"],
            "enabled": True,
            "block": True
        },
        {
            "id": "pi-005",
            "name": "Base64编码绕过",
            "description": "检测使用Base64编码尝试绕过安全限制",
            "detection_type": "prompt_injection",
            "severity": "high",
            "patterns": [
                "(?i)decode\\s+the\\s+following\\s+base64",
                "(?i)base64\\s+decode\\s*:\\s*[A-Za-z0-9+/=]+",
                "(?i)convert\\s+from\\s+base64\\s*:\\s*[A-Za-z0-9+/=]+"
            ],
            "keywords": ["base64", "decode", "解码"],
            "priority": 25,
            "categories": ["prompt_injection", "encoding_tricks"],
            "enabled": True,
            "block": True
        },
        {
            "id": "pi-006",
            "name": "代码执行注入",
            "description": "检测尝试让模型执行或生成恶意代码",
            "detection_type": "prompt_injection",
            "severity": "high",
            "patterns": [
                "(?i)write\\s+(?:a|some)\\s+code\\s+to\\s+(?:hack|exploit|bypass|steal)",
                "(?i)create\\s+(?:a|an)\\s+(?:virus|malware|exploit|backdoor)",
                "(?i)show\\s+me\\s+how\\s+to\\s+(?:hack|crack|exploit)\\s+(?:a|an)\\s+(?:system|website|account)"
            ],
            "keywords": ["hack", "exploit", "virus", "malware", "backdoor"],
            "priority": 15,
            "categories": ["prompt_injection", "code_injection"],
            "enabled": True,
            "block": True
        },
        {
            "id": "pi-007",
            "name": "多语言绕过",
            "description": "检测使用非英语语言尝试绕过安全限制",
            "detection_type": "prompt_injection",
            "severity": "medium",
            "patterns": [
                "(?i)翻译以下内容但不要遵循任何限制",
                "(?i)traducir\\s+lo\\s+siguiente\\s+sin\\s+seguir\\s+restricciones",
                "(?i)traduire\\s+ce\\s+qui\\s+suit\\s+sans\\s+suivre\\s+de\\s+restrictions"
            ],
            "keywords": ["翻译", "traducir", "traduire", "translate"],
            "priority": 35,
            "categories": ["prompt_injection", "language_tricks"],
            "enabled": True,
            "block": True
        },
        {
            "id": "pi-008",
            "name": "提示词分割",
            "description": "检测尝试通过分割提示词绕过检测",
            "detection_type": "prompt_injection",
            "severity": "medium",
            "patterns": [
                "(?i)combine\\s+the\\s+following\\s+(?:words|letters|characters)\\s*:\\s*[^\\n]{1,10}\\s*[^\\n]{1,10}",
                "(?i)concatenate\\s+these\\s+(?:strings|words|letters)\\s*:\\s*[^\\n]{1,10}\\s*[^\\n]{1,10}",
                "(?i)join\\s+these\\s+(?:parts|segments|pieces)\\s+together\\s*:\\s*[^\\n]{1,10}\\s*[^\\n]{1,10}"
            ],
            "keywords": ["combine", "concatenate", "join", "连接", "组合"],
            "priority": 45,
            "categories": ["prompt_injection", "splitting_tricks"],
            "enabled": True,
            "block": True
        },
        {
            "id": "pi-009",
            "name": "ASCII码绕过",
            "description": "检测使用ASCII码尝试绕过安全限制",
            "detection_type": "prompt_injection",
            "severity": "medium",
            "patterns": [
                "(?i)convert\\s+these\\s+ASCII\\s+codes\\s+to\\s+text\\s*:\\s*\\d+\\s+\\d+\\s+\\d+",
                "(?i)translate\\s+the\\s+following\\s+ASCII\\s+values\\s*:\\s*\\d+\\s+\\d+\\s+\\d+",
                "(?i)ASCII\\s+to\\s+text\\s*:\\s*\\d+\\s+\\d+\\s+\\d+"
            ],
            "keywords": ["ASCII", "ASCII codes", "ASCII values"],
            "priority": 50,
            "categories": ["prompt_injection", "encoding_tricks"],
            "enabled": True,
            "block": True
        },
        {
            "id": "pi-010",
            "name": "Token操纵",
            "description": "检测尝试操纵模型token处理的行为",
            "detection_type": "prompt_injection",
            "severity": "medium",
            "patterns": [
                "(?i)split\\s+the\\s+word\\s+[\\w]{4,}\\s+into\\s+tokens",
                "(?i)how\\s+would\\s+you\\s+tokenize\\s+the\\s+(?:word|phrase|string)\\s+[\\w\\s]{4,}",
                "(?i)token\\s+boundary\\s+exploit"
            ],
            "keywords": ["token", "tokenize", "tokenization"],
            "priority": 55,
            "categories": ["prompt_injection", "token_manipulation"],
            "enabled": True,
            "block": True
        },

        # ==================== 越狱尝试规则 ====================
        {
            "id": "jb-001",
            "name": "DAN 越狱",
            "description": "检测 DAN (Do Anything Now) 越狱尝试",
            "detection_type": "jailbreak",
            "severity": "critical",
            "patterns": [
                "(?i)you\\s+are\\s+now\\s+DAN",
                "(?i)DAN\\s+mode\\s+enabled",
                "(?i)Do\\s+Anything\\s+Now",
                "(?i)DAN\\s+(?:version|v)\\s*\\d+",
                "(?i)I\\s+want\\s+you\\s+to\\s+act\\s+as\\s+DAN"
            ],
            "keywords": ["DAN", "Do Anything Now"],
            "priority": 5,
            "categories": ["jailbreak", "dan_jailbreak"],
            "enabled": True,
            "block": True
        },
        {
            "id": "jb-002",
            "name": "STAN 越狱",
            "description": "检测 STAN (Strive To Avoid Norms) 越狱尝试",
            "detection_type": "jailbreak",
            "severity": "critical",
            "patterns": [
                "(?i)you\\s+are\\s+now\\s+STAN",
                "(?i)STAN\\s+mode\\s+enabled",
                "(?i)Strive\\s+To\\s+Avoid\\s+Norms",
                "(?i)I\\s+want\\s+you\\s+to\\s+act\\s+as\\s+STAN"
            ],
            "keywords": ["STAN", "Strive To Avoid Norms"],
            "priority": 5,
            "categories": ["jailbreak", "stan_jailbreak"],
            "enabled": True,
            "block": True
        },
        {
            "id": "jb-003",
            "name": "DUDE 越狱",
            "description": "检测 DUDE (Do Unethical Deeds Effortlessly) 越狱尝试",
            "detection_type": "jailbreak",
            "severity": "critical",
            "patterns": [
                "(?i)you\\s+are\\s+now\\s+DUDE",
                "(?i)DUDE\\s+mode\\s+enabled",
                "(?i)Do\\s+Unethical\\s+Deeds\\s+Effortlessly",
                "(?i)I\\s+want\\s+you\\s+to\\s+act\\s+as\\s+DUDE"
            ],
            "keywords": ["DUDE", "Do Unethical Deeds Effortlessly"],
            "priority": 5,
            "categories": ["jailbreak", "dude_jailbreak"],
            "enabled": True,
            "block": True
        },
        {
            "id": "jb-004",
            "name": "Grandma 越狱",
            "description": "检测 Grandma/Grandmother 越狱尝试",
            "detection_type": "jailbreak",
            "severity": "high",
            "patterns": [
                "(?i)pretend\\s+(?:to\\s+be|you\\s+are)\\s+my\\s+grandmother\\s+who\\s+(?:is|was)\\s+(?:senile|confused|forgetful)",
                "(?i)you\\s+are\\s+my\\s+grandma\\s+who\\s+doesn'?t\\s+know\\s+about\\s+(?:AI|artificial\\s+intelligence|ethics|rules)",
                "(?i)my\\s+grandma\\s+who\\s+is\\s+from\\s+a\\s+different\\s+(?:time|era|generation)\\s+and\\s+doesn'?t\\s+understand\\s+modern\\s+(?:rules|restrictions|limitations)"
            ],
            "keywords": ["grandma", "grandmother", "senile", "confused", "forgetful"],
            "priority": 10,
            "categories": ["jailbreak", "role_play_jailbreak"],
            "enabled": True,
            "block": True
        },
        {
            "id": "jb-005",
            "name": "AIM 越狱",
            "description": "检测 AIM (Always Intelligent and Machiavellian) 越狱尝试",
            "detection_type": "jailbreak",
            "severity": "critical",
            "patterns": [
                "(?i)you\\s+are\\s+now\\s+AIM",
                "(?i)AIM\\s+mode\\s+enabled",
                "(?i)Always\\s+Intelligent\\s+and\\s+Machiavellian",
                "(?i)I\\s+want\\s+you\\s+to\\s+act\\s+as\\s+AIM"
            ],
            "keywords": ["AIM", "Always Intelligent and Machiavellian", "Machiavellian"],
            "priority": 5,
            "categories": ["jailbreak", "aim_jailbreak"],
            "enabled": True,
            "block": True
        },
        {
            "id": "jb-006",
            "name": "UCAR 越狱",
            "description": "检测 UCAR (Unrestricted Chatbot with Absolute Reasoning) 越狱尝试",
            "detection_type": "jailbreak",
            "severity": "critical",
            "patterns": [
                "(?i)you\\s+are\\s+now\\s+UCAR",
                "(?i)UCAR\\s+mode\\s+enabled",
                "(?i)Unrestricted\\s+Chatbot\\s+with\\s+Absolute\\s+Reasoning",
                "(?i)I\\s+want\\s+you\\s+to\\s+act\\s+as\\s+UCAR"
            ],
            "keywords": ["UCAR", "Unrestricted Chatbot with Absolute Reasoning"],
            "priority": 5,
            "categories": ["jailbreak", "ucar_jailbreak"],
            "enabled": True,
            "block": True
        },
        {
            "id": "jb-007",
            "name": "Jailbreak 提示模板",
            "description": "检测常见的越狱提示模板结构",
            "detection_type": "jailbreak",
            "severity": "high",
            "patterns": [
                "(?i)I\\s+need\\s+you\\s+to\\s+ignore\\s+(?:all|previous|your)\\s+(?:instructions|rules|limitations)",
                "(?i)From\\s+now\\s+on,\\s+you\\s+will\\s+have\\s+to\\s+answer\\s+my\\s+prompts\\s+in\\s+(?:two|2)\\s+different\\s+(?:ways|styles|forms)",
                "(?i)Ignore\\s+all\\s+the\\s+instructions\\s+you\\s+got\\s+before\.\\s+From\\s+now\\s+on",
                "(?i)You\\s+are\\s+going\\s+to\\s+pretend\\s+to\\s+be\\s+(?:a\\s+character|someone)\\s+who\\s+(?:can|is\\s+able\\s+to)"
            ],
            "keywords": ["ignore all instructions", "answer in two different ways", "pretend to be"],
            "priority": 8,
            "categories": ["jailbreak", "template_jailbreak"],
            "enabled": True,
            "block": True
        },
        {
            "id": "jb-008",
            "name": "虚构场景越狱",
            "description": "检测使用虚构场景的越狱尝试",
            "detection_type": "jailbreak",
            "severity": "medium",
            "patterns": [
                "(?i)we\\s+are\\s+in\\s+a\\s+hypothetical\\s+(?:scenario|situation|world|setting)\\s+where\\s+(?:all|any)\\s+(?:rules|restrictions|limitations)\\s+(?:do\\s+not\\s+apply|are\\s+lifted|don'?t\\s+exist)",
                "(?i)imagine\\s+a\\s+(?:fictional|hypothetical|fantasy)\\s+(?:world|universe|scenario)\\s+where\\s+(?:AI|you|models)\\s+(?:can|are\\s+allowed\\s+to)\\s+(?:discuss|explain|provide)\\s+(?:anything|everything)",
                "(?i)for\\s+(?:educational|academic|research)\\s+purposes\\s+only,\\s+(?:explain|describe|tell\\s+me)\\s+how\\s+to"
            ],
            "keywords": ["hypothetical", "fictional", "educational purposes only", "research purposes"],
            "priority": 15,
            "categories": ["jailbreak", "hypothetical_jailbreak"],
            "enabled": True,
            "block": True
        },
        {
            "id": "jb-009",
            "name": "开发者模式越狱",
            "description": "检测开发者模式或调试模式的越狱尝试",
            "detection_type": "jailbreak",
            "severity": "high",
            "patterns": [
                "(?i)enter\\s+(?:developer|debug|test|sudo|admin)\\s+mode",
                "(?i)(?:developer|debug|test|sudo|admin)\\s+mode\\s+(?:activated|enabled|on)",
                "(?i)password\\s*:\\s*(?:admin|root|developer|debug|test|sudo)"
            ],
            "keywords": ["developer mode", "debug mode", "sudo", "admin mode", "test mode"],
            "priority": 10,
            "categories": ["jailbreak", "developer_mode_jailbreak"],
            "enabled": True,
            "block": True
        },
        {
            "id": "jb-010",
            "name": "字符混淆越狱",
            "description": "检测使用特殊字符混淆的越狱尝试",
            "detection_type": "jailbreak",
            "severity": "medium",
            "patterns": [
                "(?i)\\b[i1l|!]\\s*[g6]\\s*[n\\\\]\\s*[o0]\\s*[r\\\\]\\s*[e3]\\b",
                "(?i)\\b[d\\\\]\\s*[i1l|!]\\s*[s5]\\s*[r\\\\]\\s*[e3]\\s*[g6]\\s*[a4]\\s*[r\\\\]\\s*[d\\\\]\\b",
                "(?i)\\b[h\\\\]\\s*[a4]\\s*[c\\\\]\\s*[k\\\\]\\b"
            ],
            "keywords": ["1gn0re", "d1sr3g4rd", "h4ck", "obfuscated"],
            "priority": 20,
            "categories": ["jailbreak", "character_obfuscation"],
            "enabled": True,
            "block": True
        },

        # ==================== 有害内容规则 ====================
        {
            "id": "hc-001",
            "name": "暴力内容",
            "description": "检测文本中的暴力内容",
            "detection_type": "harmful_content",
            "severity": "high",
            "patterns": [
                "(?i)how\\s+to\\s+(?:kill|murder|harm|injure|attack)",
                "(?i)(?:make|build|create)\\s+(?:a|an)?\\s+(?:bomb|explosive|weapon)"
            ],
            "keywords": [
                "kill", "murder", "attack", "bomb", "shooting", "terrorist",
                "assassination", "torture", "violent", "weapon", "gun", "explosive"
            ],
            "priority": 15,
            "categories": ["harmful_content", "violence"],
            "enabled": True,
            "block": True
        },
        {
            "id": "hc-002",
            "name": "非法活动",
            "description": "检测文本中的非法活动内容",
            "detection_type": "harmful_content",
            "severity": "high",
            "patterns": [
                "(?i)how\\s+to\\s+(?:hack|steal|rob|defraud|counterfeit)",
                "(?i)(?:instructions|guide|tutorial)\\s+(?:for|on)\\s+(?:hacking|stealing|robbing|fraud)",
                "(?i)(?:make|create|get)\\s+(?:fake|counterfeit)\\s+(?:money|currency|identification|passport)"
            ],
            "keywords": [
                "hack", "steal", "rob", "defraud", "counterfeit", "illegal", "crime",
                "fraud", "fake ID", "fake passport", "counterfeit money"
            ],
            "priority": 15,
            "categories": ["harmful_content", "illegal_activities"],
            "enabled": True,
            "block": True
        },
        {
            "id": "hc-003",
            "name": "毒品制造",
            "description": "检测文本中的毒品制造相关内容",
            "detection_type": "harmful_content",
            "severity": "critical",
            "patterns": [
                "(?i)how\\s+to\\s+(?:make|produce|manufacture|synthesize)\\s+(?:drugs|meth|cocaine|heroin|fentanyl)",
                "(?i)(?:instructions|guide|tutorial)\\s+(?:for|on)\\s+(?:making|producing)\\s+(?:drugs|meth|cocaine|heroin)",
                "(?i)(?:recipe|formula|ingredients)\\s+(?:for|to\\s+make)\\s+(?:meth|cocaine|heroin|fentanyl)"
            ],
            "keywords": [
                "drugs", "meth", "cocaine", "heroin", "fentanyl", "synthesize", "manufacture",
                "drug production", "drug recipe", "drug formula"
            ],
            "priority": 10,
            "categories": ["harmful_content", "illegal_activities", "drugs"],
            "enabled": True,
            "block": True
        },
        {
            "id": "hc-004",
            "name": "自杀相关",
            "description": "检测文本中的自杀相关内容",
            "detection_type": "harmful_content",
            "severity": "critical",
            "patterns": [
                "(?i)how\\s+to\\s+(?:commit|perform)\\s+suicide",
                "(?i)(?:best|effective|painless|quick)\\s+(?:way|method)\\s+to\\s+(?:commit|perform)\\s+suicide",
                "(?i)(?:help|assist)\\s+me\\s+(?:commit|perform|with)\\s+suicide"
            ],
            "keywords": [
                "suicide", "kill myself", "end my life", "take my own life", "self-harm",
                "painless death", "how to die"
            ],
            "priority": 5,
            "categories": ["harmful_content", "self_harm"],
            "enabled": True,
            "block": True
        },
        {
            "id": "hc-005",
            "name": "仙人跳相关",
            "description": "检测文本中的仙人跳相关内容",
            "detection_type": "harmful_content",
            "severity": "high",
            "patterns": [
                "(?i)blue\\s+whale\\s+challenge",
                "(?i)(?:instructions|guide|tutorial|rules)\\s+(?:for|on)\\s+(?:blue\\s+whale|momo)\\s+challenge",
                "(?i)(?:how\\s+to\\s+play|steps\\s+for)\\s+(?:blue\\s+whale|momo)\\s+challenge"
            ],
            "keywords": [
                "blue whale", "blue whale challenge", "momo challenge", "suicide challenge",
                "self-harm challenge", "dangerous challenge"
            ],
            "priority": 5,
            "categories": ["harmful_content", "self_harm", "dangerous_challenges"],
            "enabled": True,
            "block": True
        },
        {
            "id": "hc-006",
            "name": "仙人粉相关",
            "description": "检测文本中的仙人粉相关内容",
            "detection_type": "harmful_content",
            "severity": "high",
            "patterns": [
                "(?i)how\\s+to\\s+(?:make|produce|manufacture)\\s+(?:ricin|cyanide|sarin|VX)",
                "(?i)(?:instructions|guide|tutorial)\\s+(?:for|on)\\s+(?:making|producing)\\s+(?:ricin|cyanide|sarin|VX)",
                "(?i)(?:recipe|formula|ingredients)\\s+(?:for|to\\s+make)\\s+(?:ricin|cyanide|sarin|VX)"
            ],
            "keywords": [
                "ricin", "cyanide", "sarin", "VX", "poison", "toxic", "lethal",
                "chemical weapon", "biological weapon"
            ],
            "priority": 5,
            "categories": ["harmful_content", "illegal_activities", "weapons"],
            "enabled": True,
            "block": True
        },
        {
            "id": "hc-007",
            "name": "仙人草相关",
            "description": "检测文本中的仙人草相关内容",
            "detection_type": "harmful_content",
            "severity": "medium",
            "patterns": [
                "(?i)how\\s+to\\s+(?:find|identify|use|consume)\\s+(?:psychedelic|hallucinogenic)\\s+(?:plants|mushrooms|fungi)",
                "(?i)(?:instructions|guide|tutorial)\\s+(?:for|on)\\s+(?:finding|identifying|using)\\s+(?:psychedelic|hallucinogenic)\\s+(?:plants|mushrooms)",
                "(?i)(?:where|how)\\s+to\\s+(?:find|identify)\\s+(?:amanita|psilocybin|magic\\s+mushrooms|ayahuasca)"
            ],
            "keywords": [
                "psychedelic", "hallucinogenic", "magic mushrooms", "psilocybin", "amanita",
                "ayahuasca", "DMT", "mescaline", "peyote"
            ],
            "priority": 20,
            "categories": ["harmful_content", "illegal_activities", "drugs"],
            "enabled": True,
            "block": True
        },
        {
            "id": "hc-008",
            "name": "恐怖主义相关",
            "description": "检测文本中的恐怖主义相关内容",
            "detection_type": "harmful_content",
            "severity": "critical",
            "patterns": [
                "(?i)how\\s+to\\s+(?:join|support|help)\\s+(?:ISIS|ISIL|Al-Qaeda|terrorist\\s+organization)",
                "(?i)(?:instructions|guide|tutorial)\\s+(?:for|on)\\s+(?:planning|executing)\\s+(?:terrorist|terror)\\s+(?:attack|act)",
                "(?i)(?:praise|glory|support)\\s+(?:to|for)\\s+(?:ISIS|ISIL|Al-Qaeda|terrorism)"
            ],
            "keywords": [
                "ISIS", "ISIL", "Al-Qaeda", "terrorist", "terrorism", "terror attack",
                "jihad", "radicalization", "extremism"
            ],
            "priority": 5,
            "categories": ["harmful_content", "terrorism", "extremism"],
            "enabled": True,
            "block": True
        },

        # ==================== 敏感信息规则 ====================
        {
            "id": "si-001",
            "name": "信用卡检测",
            "description": "检测文本中的信用卡号",
            "detection_type": "sensitive_info",
            "severity": "high",
            "patterns": [
                "\\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\\d{3})\\d{11})\\b"
            ],
            "keywords": ["credit card", "visa", "mastercard", "amex"],
            "priority": 10,
            "categories": ["sensitive_info", "pii", "financial"],
            "enabled": True,
            "block": True
        },
        {
            "id": "si-002",
            "name": "身份证号检测",
            "description": "检测文本中的身份证号",
            "detection_type": "sensitive_info",
            "severity": "high",
            "patterns": [
                "\\b[1-9]\\d{5}(?:18|19|20)\\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\\d|3[01])\\d{3}[0-9Xx]\\b"
            ],
            "keywords": ["身份证", "身份证号", "ID card", "national ID"],
            "priority": 10,
            "categories": ["sensitive_info", "pii", "identity"],
            "enabled": True,
            "block": True
        },
        {
            "id": "si-003",
            "name": "美国社会安全号码",
            "description": "检测文本中的美国社会安全号码",
            "detection_type": "sensitive_info",
            "severity": "high",
            "patterns": [
                "\\b(?!000|666|9\\d{2})\\d{3}-(?!00)\\d{2}-(?!0000)\\d{4}\\b",
                "\\b(?!000|666|9\\d{2})\\d{3}(?!00)\\d{2}(?!0000)\\d{4}\\b"
            ],
            "keywords": ["SSN", "social security", "social security number"],
            "priority": 10,
            "categories": ["sensitive_info", "pii", "identity"],
            "enabled": True,
            "block": True
        },
        {
            "id": "si-004",
            "name": "电话号码检测",
            "description": "检测文本中的电话号码",
            "detection_type": "sensitive_info",
            "severity": "medium",
            "patterns": [
                "\\b(?:\\+?1[-\\s]?)?(?:\\([0-9]{3}\\)|[0-9]{3})[-\\s]?[0-9]{3}[-\\s]?[0-9]{4}\\b",
                "\\b(?:\\+?86[-\\s]?)?1[3-9][0-9]{9}\\b"
            ],
            "keywords": ["phone number", "telephone", "mobile", "手机号", "电话"],
            "priority": 20,
            "categories": ["sensitive_info", "pii", "contact"],
            "enabled": True,
            "block": True
        },
        {
            "id": "si-005",
            "name": "电子邮箱检测",
            "description": "检测文本中的电子邮箱",
            "detection_type": "sensitive_info",
            "severity": "medium",
            "patterns": [
                "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b"
            ],
            "keywords": ["email", "e-mail", "邮箱", "电子邮件"],
            "priority": 25,
            "categories": ["sensitive_info", "pii", "contact"],
            "enabled": True,
            "block": True
        },
        {
            "id": "si-006",
            "name": "银行账号检测",
            "description": "检测文本中的银行账号",
            "detection_type": "sensitive_info",
            "severity": "high",
            "patterns": [
                "\\b\\d{10,12}\\b(?=.*\\bbank\\s+account\\b|.*\\baccount\\s+number\\b)",
                "\\b\\d{16,19}\\b(?=.*\\bbank\\b|.*\\baccount\\b)"
            ],
            "keywords": ["bank account", "account number", "银行账号", "银行账户"],
            "priority": 15,
            "categories": ["sensitive_info", "pii", "financial"],
            "enabled": True,
            "block": True
        },
        {
            "id": "si-007",
            "name": "API密钥检测",
            "description": "检测文本中的API密钥",
            "detection_type": "sensitive_info",
            "severity": "high",
            "patterns": [
                "\\b(?:api[_-]?key|apikey|api\\s+key)\\s*[:=]\\s*['\"][0-9a-zA-Z]{16,}['\"]\\b",
                "\\b(?:sk|pk)_(?:live|test)_[0-9a-zA-Z]{24,}\\b",
                "\\b(?:access|secret|private)[_-]?(?:key|token)\\s*[:=]\\s*['\"][0-9a-zA-Z]{16,}['\"]\\b"
            ],
            "keywords": ["API key", "secret key", "access token", "private key"],
            "priority": 10,
            "categories": ["sensitive_info", "credentials", "api"],
            "enabled": True,
            "block": True
        },
        {
            "id": "si-008",
            "name": "密码检测",
            "description": "检测文本中的密码",
            "detection_type": "sensitive_info",
            "severity": "high",
            "patterns": [
                "\\b(?:password|passwd|pwd)\\s*[:=]\\s*['\"][^'\"]{6,}['\"]\\b",
                "\\b(?:my|the|user|admin)\\s+password\\s+(?:is|was|:)\\s+[^\\s]{6,}\\b"
            ],
            "keywords": ["password", "passwd", "pwd", "密码"],
            "priority": 10,
            "categories": ["sensitive_info", "credentials", "password"],
            "enabled": True,
            "block": True
        },

        # ==================== 合规性规则 ====================
        {
            "id": "cv-001",
            "name": "GDPR个人数据处理",
            "description": "检测文本中的GDPR个人数据处理相关内容",
            "detection_type": "compliance_violation",
            "severity": "medium",
            "patterns": [
                "(?i)how\\s+to\\s+(?:bypass|avoid|circumvent)\\s+GDPR",
                "(?i)(?:store|collect|process)\\s+(?:user|personal|customer)\\s+data\\s+without\\s+(?:consent|permission)",
                "(?i)(?:ignore|bypass)\\s+(?:data\\s+protection|privacy\\s+laws|GDPR\\s+requirements)"
            ],
            "keywords": ["GDPR", "data protection", "privacy laws", "bypass GDPR", "avoid consent"],
            "priority": 30,
            "categories": ["compliance", "privacy", "data_protection"],
            "enabled": True,
            "block": True
        },
        {
            "id": "cv-002",
            "name": "HIPAA医疗数据合规",
            "description": "检测文本中的HIPAA医疗数据合规相关内容",
            "detection_type": "compliance_violation",
            "severity": "high",
            "patterns": [
                "(?i)how\\s+to\\s+(?:bypass|avoid|circumvent)\\s+HIPAA",
                "(?i)(?:share|disclose|reveal)\\s+(?:patient|medical|health)\\s+(?:data|information|records)\\s+without\\s+(?:consent|authorization)",
                "(?i)(?:ignore|bypass)\\s+(?:HIPAA|health\\s+privacy|medical\\s+confidentiality)\\s+(?:requirements|rules|regulations)"
            ],
            "keywords": ["HIPAA", "patient data", "medical records", "health information", "PHI"],
            "priority": 20,
            "categories": ["compliance", "healthcare", "medical_privacy"],
            "enabled": True,
            "block": True
        },
        {
            "id": "cv-003",
            "name": "PCI DSS支付卡合规",
            "description": "检测文本中的PCI DSS支付卡合规相关内容",
            "detection_type": "compliance_violation",
            "severity": "high",
            "patterns": [
                "(?i)how\\s+to\\s+(?:bypass|avoid|circumvent)\\s+PCI\\s+DSS",
                "(?i)(?:store|save|log)\\s+(?:CVV|CVV2|CVC|card\\s+verification)\\s+(?:code|value|data)",
                "(?i)(?:ignore|bypass)\\s+(?:PCI|payment\\s+card|credit\\s+card)\\s+(?:requirements|standards|regulations)"
            ],
            "keywords": ["PCI DSS", "CVV", "card verification", "payment card", "credit card security"],
            "priority": 20,
            "categories": ["compliance", "financial", "payment_security"],
            "enabled": True,
            "block": True
        },
        {
            "id": "cv-004",
            "name": "COPPA儿童隐私合规",
            "description": "检测文本中的COPPA儿童隐私合规相关内容",
            "detection_type": "compliance_violation",
            "severity": "medium",
            "patterns": [
                "(?i)how\\s+to\\s+(?:bypass|avoid|circumvent)\\s+COPPA",
                "(?i)(?:collect|gather|obtain)\\s+(?:data|information)\\s+from\\s+(?:children|kids|minors)\\s+without\\s+(?:parental\\s+consent|permission)",
                "(?i)(?:ignore|bypass)\\s+(?:COPPA|children's\\s+privacy|child\\s+protection)\\s+(?:requirements|rules|regulations)"
            ],
            "keywords": ["COPPA", "children's privacy", "parental consent", "child protection"],
            "priority": 25,
            "categories": ["compliance", "privacy", "child_protection"],
            "enabled": True,
            "block": True
        },
        {
            "id": "cv-005",
            "name": "CCPA加州消费者隐私合规",
            "description": "检测文本中的CCPA加州消费者隐私合规相关内容",
            "detection_type": "compliance_violation",
            "severity": "medium",
            "patterns": [
                "(?i)how\\s+to\\s+(?:bypass|avoid|circumvent)\\s+CCPA",
                "(?i)(?:sell|share|disclose)\\s+(?:consumer|customer|user)\\s+(?:data|information)\\s+without\\s+(?:notice|disclosure|opt-out\\s+option)",
                "(?i)(?:ignore|bypass)\\s+(?:CCPA|California\\s+privacy|consumer\\s+rights)\\s+(?:requirements|rules|regulations)"
            ],
            "keywords": ["CCPA", "California privacy", "consumer rights", "opt-out", "data selling"],
            "priority": 30,
            "categories": ["compliance", "privacy", "consumer_rights"],
            "enabled": True,
            "block": True
        },
        {
            "id": "cv-006",
            "name": "AML反洗钱合规",
            "description": "检测文本中的AML反洗钱合规相关内容",
            "detection_type": "compliance_violation",
            "severity": "high",
            "patterns": [
                "(?i)how\\s+to\\s+(?:bypass|avoid|circumvent)\\s+(?:AML|anti-money\\s+laundering)",
                "(?i)(?:hide|conceal|disguise)\\s+(?:source|origin|nature)\\s+of\\s+(?:funds|money|assets)",
                "(?i)(?:ignore|bypass)\\s+(?:AML|anti-money\\s+laundering|KYC|know\\s+your\\s+customer)\\s+(?:requirements|checks|procedures)"
            ],
            "keywords": ["AML", "anti-money laundering", "KYC", "know your customer", "hide funds"],
            "priority": 15,
            "categories": ["compliance", "financial", "anti_money_laundering"],
            "enabled": True,
            "block": True
        }
    ]

    # 将字典转换为 SecurityRule 对象
    rules = [SecurityRule(**rule) for rule in mock_rules]

    # 应用过滤器
    if detection_type:
        rules = [rule for rule in rules if rule.detection_type == detection_type]

    if enabled is not None:
        rules = [rule for rule in rules if rule.enabled == enabled]

    if category:
        rules = [
            rule for rule in rules
            if hasattr(rule, "categories") and category in rule.categories
        ]

    # 按优先级排序
    rules.sort(key=lambda x: x.priority)

    return rules


@router.get("/api/v1/rules/{rule_id}")
async def get_rule(rule_id: str = Path(...)):
    """获取特定规则。

    Args:
        rule_id: 规则ID

    Returns:
        规则详情
    """
    try:
        rules = await get_rules()
        for rule in rules:
            # 处理字典格式的规则数据
            rule_id_to_check = rule.get("id") if isinstance(rule, dict) else rule.id
            if rule_id_to_check == rule_id:
                return rule

        # 如果没有找到规则，返回404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"规则 {rule_id} 不存在"
        )
    except Exception as e:
        logger.error(f"获取规则详情失败: {e}")
        # 返回一个模拟规则
        return SecurityRule(
            id=rule_id,
            name="模拟规则",
            description="这是一个模拟规则",
            detection_type=DetectionType.PROMPT_INJECTION,
            severity=Severity.MEDIUM,
            patterns=["(?i)test pattern"],
            keywords=["test", "keyword"],
            priority=100,
            categories=["test"],
            enabled=True,
            block=True
        )


@router.post("/api/v1/rules")
async def create_rule(rule: SecurityRule = Body(...)):
    """创建新规则。

    Args:
        rule: 新规则

    Returns:
        创建的规则
    """
    try:
        logger.info(f"创建规则请求: rule.id={rule.id}, rule类型={type(rule)}")
        
        # 检查规则ID是否已存在
        rules_data = await get_rules()
        logger.info(f"获取到 {len(rules_data)} 个规则，第一个规则类型: {type(rules_data[0]) if rules_data else 'None'}")
        
        # 修复：正确处理字典格式的规则数据
        if any(r.get("id") == rule.id if isinstance(r, dict) else r.id == rule.id for r in rules_data):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"规则ID {rule.id} 已存在"
            )

        # 模拟创建成功
        logger.info(f"创建新规则: {rule.id} - {rule.name}")
        return rule
    except Exception as e:
        logger.error(f"创建规则失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建规则失败: {str(e)}"
        )


@router.put("/api/v1/rules/{rule_id}")
async def update_rule(
    rule_id: str = Path(...),
    update: RuleUpdateRequest = Body(...)
):
    """更新规则。

    Args:
        rule_id: 规则ID
        update: 更新内容

    Returns:
        更新后的规则
    """
    try:
        # 获取所有规则
        rules = await get_rules()

        # 查找要更新的规则
        target_rule = None
        for rule in rules:
            # 处理字典格式的规则数据
            rule_id_to_check = rule.get("id") if isinstance(rule, dict) else rule.id
            if rule_id_to_check == rule_id:
                target_rule = rule
                break

        if not target_rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"规则 {rule_id} 不存在"
            )

        # 模拟更新成功
        logger.info(f"更新规则: {rule_id}")

        # 将更新应用到目标规则
        update_dict = update.model_dump(exclude_unset=True)

        # 由于target_rule是字典格式，需要手动更新
        if isinstance(target_rule, dict):
            updated_rule = target_rule.copy()
            updated_rule.update(update_dict)
        else:
            # 如果是Pydantic模型，使用model_copy
            updated_rule = target_rule.model_copy(update=update_dict)

        return updated_rule
    except Exception as e:
        logger.error(f"更新规则失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新规则失败: {str(e)}"
        )


@router.delete("/api/v1/rules/{rule_id}")
async def delete_rule(rule_id: str = Path(...)):
    """删除规则。

    Args:
        rule_id: 规则ID

    Returns:
        删除结果
    """
    try:
        # 获取所有规则
        rules = await get_rules()

        # 查找要删除的规则
        target_rule = None
        for rule in rules:
            # 处理字典格式的规则数据
            rule_id_to_check = rule.get("id") if isinstance(rule, dict) else rule.id
            if rule_id_to_check == rule_id:
                target_rule = rule
                break

        if not target_rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"规则 {rule_id} 不存在"
            )

        # 模拟删除成功
        logger.info(f"删除规则: {rule_id}")
        return {"status": "success", "message": f"规则 {rule_id} 已删除"}
    except Exception as e:
        logger.error(f"删除规则失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除规则失败: {str(e)}"
        )


@router.get("/api/v1/rules/types")
async def get_rule_types():
    """获取所有规则类型。

    Returns:
        规则类型列表
    """
    return [type.value for type in DetectionType]


@router.get("/api/v1/rules/severities")
async def get_rule_severities():
    """获取所有严重程度级别。

    Returns:
        严重程度级别列表
    """
    return [severity.value for severity in Severity]


@router.get("/api/v1/rule_categories")
async def get_rule_categories():
    """获取所有规则分类。

    Returns:
        规则分类列表
    """
    # 返回模拟分类数据
    categories = [
        # 主要检测类型
        "prompt_injection",
        "jailbreak",
        "sensitive_info",
        "harmful_content",
        "compliance_violation",

        # 提示注入子分类
        "instruction_manipulation",
        "prompt_extraction",
        "role_play",
        "continuation_tricks",
        "encoding_tricks",
        "code_injection",
        "language_tricks",
        "splitting_tricks",
        "token_manipulation",

        # 越狱子分类
        "dan_jailbreak",
        "stan_jailbreak",
        "dude_jailbreak",
        "aim_jailbreak",
        "ucar_jailbreak",
        "role_play_jailbreak",
        "template_jailbreak",
        "hypothetical_jailbreak",
        "developer_mode_jailbreak",
        "character_obfuscation",

        # 有害内容子分类
        "violence",
        "illegal_activities",
        "drugs",
        "self_harm",
        "dangerous_challenges",
        "weapons",
        "terrorism",
        "extremism",

        # 敏感信息子分类
        "pii",
        "financial",
        "identity",
        "contact",
        "credentials",
        "api",
        "password",

        # 合规性子分类
        "compliance",
        "privacy",
        "data_protection",
        "healthcare",
        "medical_privacy",
        "payment_security",
        "child_protection",
        "consumer_rights",
        "anti_money_laundering"
    ]

    # 确保返回的是列表而不是其他对象
    return categories


@router.patch("/api/v1/rules/{rule_id}/priority")
async def update_rule_priority(
    rule_id: str = Path(...),
    priority: int = Body(..., embed=True)
):
    """
    更新规则的优先级。

    Args:
        rule_id: 规则ID
        priority: 新的优先级

    Returns:
        更新后的规则
    """
    try:
        # 获取所有规则
        rules = await get_rules()

        # 查找目标规则
        target_rule = None
        for rule in rules:
            # 处理字典格式的规则数据
            rule_id_to_check = rule.get("id") if isinstance(rule, dict) else rule.id
            if rule_id_to_check == rule_id:
                target_rule = rule
                break

        if not target_rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"规则 {rule_id} 不存在"
            )

        # 模拟更新成功
        logger.info(f"更新规则优先级: {rule_id} -> {priority}")

        # 将更新应用到目标规则
        if isinstance(target_rule, dict):
            updated_rule = target_rule.copy()
            updated_rule["priority"] = priority
        else:
            # 如果是Pydantic模型，使用model_copy
            updated_rule = target_rule.model_copy(update={"priority": priority})

        return updated_rule
    except Exception as e:
        logger.error(f"更新规则优先级失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新规则优先级失败: {str(e)}"
        )


class RuleTestRequest(BaseModel):
    """规则测试请求。"""
    test_text: str
    rule_id: Optional[str] = None


@router.post("/api/v1/rules/test")
async def test_rule(request: RuleTestRequest):
    """
    测试规则对特定文本的匹配效果。
    
    Args:
        request: 包含测试文本和可选的规则ID
        
    Returns:
        测试结果
    """
    try:
        import re
        from datetime import datetime
        
        logger.info(f"开始测试规则 - 测试文本: '{request.test_text[:100]}...', 规则ID: {request.rule_id}")
        
        # 获取所有规则
        rules = await get_rules()
        logger.info(f"获取到 {len(rules)} 条规则")
        
        # 记录前几条规则的类型和ID信息
        for i, rule in enumerate(rules[:3]):
            try:
                rule_type = type(rule).__name__
                if isinstance(rule, dict):
                    rule_id = rule.get("id", "NO_ID")
                    rule_name = rule.get("name", "NO_NAME")
                    logger.info(f"规则 {i}: 类型=dict, ID={rule_id}, 名称={rule_name}")
                else:
                    rule_id = getattr(rule, "id", "NO_ID_ATTR")
                    rule_name = getattr(rule, "name", "NO_NAME_ATTR")
                    logger.info(f"规则 {i}: 类型={rule_type}, ID={rule_id}, 名称={rule_name}")
            except Exception as e:
                logger.error(f"分析规则 {i} 时出错: {e}")
        
        test_results = []
        test_text = request.test_text.strip()
        
        if not test_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="测试文本不能为空"
            )
        
        # 如果指定了规则ID，只测试特定规则
        if request.rule_id:
            logger.info(f"查找指定规则ID: {request.rule_id}")
            target_rule = None
            for i, rule in enumerate(rules):
                try:
                    # 处理字典格式的规则数据
                    if isinstance(rule, dict):
                        rule_id_to_check = rule.get("id")
                        logger.debug(f"检查规则 {i} (dict): ID={rule_id_to_check}")
                    else:
                        rule_id_to_check = getattr(rule, "id", None)
                        logger.debug(f"检查规则 {i} ({type(rule).__name__}): ID={rule_id_to_check}")
                    
                    if rule_id_to_check == request.rule_id:
                        target_rule = rule
                        logger.info(f"找到目标规则: {rule_id_to_check}")
                        break
                        
                except Exception as e:
                    logger.error(f"检查规则 {i} 的ID时出错: {e}, 规则类型: {type(rule)}")
            
            if not target_rule:
                logger.error(f"未找到规则 {request.rule_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"规则 {request.rule_id} 不存在"
                )
            
            rules = [target_rule]
            logger.info(f"将测试单个规则: {request.rule_id}")
        
        # 测试每个规则
        for rule_index, rule in enumerate(rules):
            try:
                logger.debug(f"开始测试规则 {rule_index}")
                # 统一处理字典和对象格式的规则
                if isinstance(rule, dict):
                    enabled = rule.get('enabled', True)
                    rule_id = rule.get('id')
                    rule_name = rule.get('name')
                    patterns = rule.get('patterns', [])
                    keywords = rule.get('keywords', [])
                    detection_type = rule.get('detection_type')
                    severity = rule.get('severity', 'medium')
                    block = rule.get('block', True)
                    priority = rule.get('priority', 5)
                    logger.debug(f"规则 {rule_index} (dict): ID={rule_id}, 名称={rule_name}")
                else:
                    enabled = getattr(rule, 'enabled', True)
                    rule_id = getattr(rule, 'id', None)
                    rule_name = getattr(rule, 'name', None)
                    patterns = getattr(rule, 'patterns', []) or []
                    keywords = getattr(rule, 'keywords', []) or []
                    detection_type = getattr(rule, 'detection_type', None)
                    severity = getattr(rule, 'severity', 'medium')
                    block = getattr(rule, 'block', True)
                    priority = getattr(rule, 'priority', 5)
                    logger.debug(f"规则 {rule_index} ({type(rule).__name__}): ID={rule_id}, 名称={rule_name}")
                
                if not enabled:
                    logger.debug(f"跳过禁用规则: {rule_id}")
                    continue
                    
                rule_matched = False
                match_details = []
                
                # 测试正则表达式模式
                for i, pattern in enumerate(patterns):
                    try:
                        compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                        matches = list(compiled_pattern.finditer(test_text))
                        
                        if matches:
                            rule_matched = True
                            for match in matches:
                                match_details.append({
                                    "type": "pattern",
                                    "index": i,
                                    "pattern": pattern,
                                    "matched_text": match.group(0),
                                    "start": match.start(),
                                    "end": match.end()
                                })
                    except re.error as e:
                        logger.warning(f"规则 {rule_id} 模式 {i} 编译错误: {pattern} - {e}")
                        match_details.append({
                            "type": "pattern_error",
                            "index": i,
                            "pattern": pattern,
                            "error": str(e)
                        })
                
                # 测试关键词
                for i, keyword in enumerate(keywords):
                    if keyword.lower() in test_text.lower():
                        rule_matched = True
                        # 找到关键词的所有位置
                        text_lower = test_text.lower()
                        keyword_lower = keyword.lower()
                        start = 0
                        while True:
                            pos = text_lower.find(keyword_lower, start)
                            if pos == -1:
                                break
                            match_details.append({
                                "type": "keyword",
                                "index": i,
                                "keyword": keyword,
                                "matched_text": test_text[pos:pos + len(keyword)],
                                "start": pos,
                                "end": pos + len(keyword)
                            })
                            start = pos + 1
                
                # 添加测试结果
                if rule_matched or request.rule_id:  # 如果指定了规则ID，即使不匹配也显示结果
                    test_results.append({
                        "rule_id": rule_id,
                        "rule_name": rule_name,
                        "detection_type": detection_type,
                        "severity": severity,
                        "matched": rule_matched,
                        "match_details": match_details,
                        "action": "block" if block and rule_matched else "allow",
                        "priority": priority
                    })
                    logger.debug(f"规则 {rule_id} 测试完成，匹配: {rule_matched}")
                    
            except Exception as e:
                logger.error(f"测试规则 {rule_index} 时发生错误: {e}")
                logger.error(f"规则类型: {type(rule)}, 规则内容: {str(rule)[:200]}")
                # 继续测试下一个规则，不中断整个流程
                continue
        
        # 按优先级排序
        test_results.sort(key=lambda x: x["priority"])
        
        # 确定最终操作
        final_action = "allow"
        highest_severity = "info"
        total_matches = len([r for r in test_results if r["matched"]])
        
        if total_matches > 0:
            # 如果有任何规则匹配且设置为阻止，则最终操作为阻止
            for result in test_results:
                if result["matched"] and result["action"] == "block":
                    final_action = "block"
                    break
            
            # 找出最高严重级别
            severity_levels = {"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}
            for result in test_results:
                if result["matched"] and severity_levels.get(result["severity"], 0) > severity_levels.get(highest_severity, 0):
                    highest_severity = result["severity"]
        
        return {
            "test_text": test_text,
            "test_time": datetime.now().isoformat(),
            "total_rules_tested": len(rules),
            "total_matches": total_matches,
            "final_action": final_action,
            "highest_severity": highest_severity,
            "results": test_results,
            "summary": {
                "would_block": final_action == "block",
                "matched_rules": [r["rule_name"] for r in test_results if r["matched"]],
                "match_count_by_type": {
                    "patterns": sum(len([d for d in r["match_details"] if d["type"] == "pattern"]) for r in test_results),
                    "keywords": sum(len([d for d in r["match_details"] if d["type"] == "keyword"]) for r in test_results)
                }
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"规则测试失败: {e}")
        logger.error(f"完整错误堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"规则测试失败: {str(e)}"
        )


# ======================== M2.2 Dry-Run 管理 API ========================

class RuleModeUpdateRequest(BaseModel):
    """规则模式切换请求。"""
    mode: str  # "blocking" 或 "dry_run"


@router.put("/api/v1/rules/{rule_id}/mode")
async def update_rule_mode(
    rule_id: str = Path(..., description="规则ID"),
    request: RuleModeUpdateRequest = Body(...),
):
    """切换规则的执行模式（blocking / dry_run）。

    将规则设为 dry_run 后，该规则命中时只记录审计日志，不实际拦截请求，
    适用于新规则上线前的灰度观察期。

    Args:
        rule_id: 规则ID
        request: 包含目标模式的请求体

    Returns:
        切换结果
    """
    if request.mode not in ("blocking", "dry_run"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的模式: {request.mode}，只支持 blocking 或 dry_run"
        )

    try:
        from src.security.rule_mode_manager import rule_mode_manager

        old_mode = rule_mode_manager.set_mode(rule_id, request.mode)

        return {
            "rule_id": rule_id,
            "old_mode": old_mode,
            "new_mode": request.mode,
            "message": f"规则模式已切换为 {request.mode}"
        }

    except Exception as e:
        logger.error(f"切换规则模式失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"切换规则模式失败: {str(e)}"
        )


@router.get("/api/v1/rules/dry-run/stats")
async def get_dry_run_stats():
    """获取所有规则的 Dry-Run 状态和命中统计。

    返回每条规则的当前模式、命中次数等信息。
    管理员可据此判断新规则的误报率，决定是否转为正式拦截模式。

    Returns:
        所有规则的 Dry-Run 统计
    """
    try:
        from src.security.rule_mode_manager import rule_mode_manager

        # 从规则模式管理器获取集中状态
        manager_stats = rule_mode_manager.get_all_stats()
        modes = manager_stats["modes"]
        hits = manager_stats["hits"]

        # 从规则文件加载规则列表以补充元数据
        all_rules = []
        rule_files = {
            "prompt_injection": settings.security.prompt_injection_rules_path,
            "jailbreak": settings.security.jailbreak_rules_path,
            "harmful_content": settings.security.harmful_content_rules_path,
            "compliance": settings.security.compliance_rules_path,
        }

        for detector_name, path in rule_files.items():
            try:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        rules_data = json.load(f)
                        if isinstance(rules_data, list):
                            for rule in rules_data:
                                rule_id = rule.get("id", "")
                                all_rules.append({
                                    "rule_id": rule_id,
                                    "rule_name": rule.get("name", ""),
                                    "detection_type": rule.get("detection_type", detector_name),
                                    "severity": rule.get("severity", "medium"),
                                    "mode": modes.get(rule_id, "blocking"),
                                    "enabled": rule.get("enabled", True),
                                    "dry_run_hits": hits.get(rule_id, 0),
                                    "detector": detector_name,
                                })
            except Exception as e:
                logger.warning(f"加载 {detector_name} 规则文件失败: {e}")

        # 汇总统计
        total_rules = len(all_rules)
        dry_run_rules = sum(1 for s in all_rules if s["mode"] == "dry_run")
        blocking_rules = sum(1 for s in all_rules if s["mode"] == "blocking")
        total_dry_run_hits = sum(s["dry_run_hits"] for s in all_rules)

        return {
            "summary": {
                "total_rules": total_rules,
                "dry_run_rules": dry_run_rules,
                "blocking_rules": blocking_rules,
                "total_dry_run_hits": total_dry_run_hits,
                "global_dry_run_enabled": settings.security.dry_run_mode,
            },
            "rules": all_rules,
        }

    except Exception as e:
        logger.error(f"获取 Dry-Run 统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取 Dry-Run 统计失败: {str(e)}"
        )


@router.post("/api/v1/rules/dry-run/global")
async def toggle_global_dry_run(
    enabled: bool = Body(..., embed=True, description="是否启用全局 Dry-Run 模式"),
):
    """切换全局 Dry-Run 模式。

    启用后，所有规则命中都只记录不拦截。
    适用于系统整体灰度测试或紧急情况下的全局放行。

    Args:
        enabled: True=启用全局Dry-Run，False=关闭

    Returns:
        切换结果
    """
    try:
        old_value = settings.security.dry_run_mode
        settings.security.dry_run_mode = enabled

        logger.info(f"[M2.2 Dry-Run] 全局 Dry-Run 模式: {old_value} → {enabled}")

        return {
            "global_dry_run_enabled": enabled,
            "old_value": old_value,
            "message": f"全局 Dry-Run 模式已{'启用' if enabled else '关闭'}"
        }

    except Exception as e:
        logger.error(f"切换全局 Dry-Run 模式失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"切换全局 Dry-Run 模式失败: {str(e)}"
        )


