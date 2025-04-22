"""规则管理API。"""

import json
import os
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Path, Query, status
from pydantic import BaseModel

from src.config import settings
from src.logger import logger
from src.models_interceptor import DetectionType, SecurityRule, Severity


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
    # 返回模拟规则数据
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
            if rule.id == rule_id:
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
        # 检查规则ID是否已存在
        rules = await get_rules()
        if any(r.id == rule.id for r in rules):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"规则ID {rule.id} 已存在"
            )

        # 模拟创建成功
        logger.info(f"创建新规则: {rule.id} - {rule.name}")
        return rule
    except Exception as e:
        logger.error(f"创建规则失败: {e}")
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
            if rule.id == rule_id:
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
            if rule.id == rule_id:
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


@router.get("/api/v1/rules/categories")
async def get_rule_categories():
    """获取所有规则分类。

    Returns:
        规则分类列表
    """
    # 返回模拟分类数据
    return [
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
            if rule.id == rule_id:
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
        updated_rule = target_rule.model_copy(update={"priority": priority})

        return updated_rule
    except Exception as e:
        logger.error(f"更新规则优先级失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新规则优先级失败: {str(e)}"
        )
