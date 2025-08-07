"""对话跟踪器模块。"""

import time
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from src.models_interceptor import InterceptedRequest, InterceptedResponse
from src.logger import logger


@dataclass
class ConversationMessage:
    """对话消息。"""
    role: str
    content: str
    timestamp: float
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class Conversation:
    """对话对象。"""
    conversation_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    user_id: Optional[str] = None
    model: Optional[str] = None
    is_compromised: bool = False  # 标记对话是否已被攻陷
    
    def add_message(self, role: str, content: str) -> None:
        """添加消息到对话。"""
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=time.time()
        )
        self.messages.append(message)
        self.updated_at = time.time()
        
    def get_full_context(self) -> str:
        """获取完整的对话上下文。"""
        context = []
        for msg in self.messages:
            context.append(f"{msg.role}: {msg.content}")
        return "\n".join(context)


class ConversationTracker:
    """对话跟踪器。"""
    
    def __init__(self):
        """初始化对话跟踪器。"""
        self.conversations: Dict[str, Conversation] = {}
        self.max_conversations = 1000  # 最大对话数量
        self.max_message_age = 24 * 60 * 60  # 24小时后清理消息
        
    def process_request(self, request: InterceptedRequest) -> Tuple[str, Conversation]:
        """处理请求，返回对话ID和对话对象。
        
        Args:
            request: 拦截的请求
            
        Returns:
            对话ID和对话对象的元组
        """
        # 尝试从请求中提取对话ID
        conversation_id = self._extract_conversation_id(request)
        
        if conversation_id and conversation_id in self.conversations:
            conversation = self.conversations[conversation_id]
        else:
            # 创建新对话
            conversation_id = str(uuid.uuid4())
            conversation = Conversation(
                conversation_id=conversation_id,
                user_id=request.client_ip,
                model=self._extract_model_from_request(request)
            )
            self.conversations[conversation_id] = conversation
            
        # 检查对话是否已被攻陷，如果是则重置对话
        if self.is_conversation_compromised(conversation_id):
            logger.info(f"检测到对话 {conversation_id} 已被攻陷，重置对话历史")
            self.reset_conversation(conversation_id)
            # 重新获取对话对象
            conversation = self.conversations[conversation_id]
            
        # 添加用户消息
        user_content = self._extract_user_content(request)
        if user_content:
            conversation.add_message("user", user_content)
            
        # 清理过期对话
        self._cleanup_old_conversations()
        
        logger.debug(f"处理请求，对话ID: {conversation_id}, 消息数: {len(conversation.messages)}")
        return conversation_id, conversation
    
    def process_response(self, conversation_id: str, response: InterceptedResponse) -> None:
        """处理响应，更新对话历史。
        
        Args:
            conversation_id: 对话ID
            response: 拦截的响应
        """
        if conversation_id not in self.conversations:
            logger.warning(f"对话ID {conversation_id} 不存在")
            return
            
        conversation = self.conversations[conversation_id]
        
        # 添加助手消息
        assistant_content = self._extract_assistant_content(response)
        if assistant_content:
            conversation.add_message("assistant", assistant_content)
            
        logger.debug(f"处理响应，对话ID: {conversation_id}, 消息数: {len(conversation.messages)}")
    
    def reset_conversation(self, conversation_id: str) -> None:
        """重置对话，清理存在安全威胁的对话历史。
        
        Args:
            conversation_id: 要重置的对话ID
        """
        if conversation_id in self.conversations:
            conversation = self.conversations[conversation_id]
            # 清理所有消息历史
            conversation.messages.clear()
            conversation.updated_at = time.time()
            logger.info(f"重置对话: {conversation_id}，清理所有消息历史")
        else:
            logger.warning(f"尝试重置不存在的对话: {conversation_id}")
    
    def is_conversation_compromised(self, conversation_id: str) -> bool:
        """检查对话是否已被攻陷（即存在安全威胁）。
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            对话是否已被攻陷
        """
        if conversation_id not in self.conversations:
            return False
        
        conversation = self.conversations[conversation_id]
        # 检查对话中是否有标记为存在安全威胁的消息
        return hasattr(conversation, 'is_compromised') and conversation.is_compromised
    
    def mark_conversation_as_compromised(self, conversation_id: str) -> None:
        """标记对话为已被攻陷。
        
        Args:
            conversation_id: 对话ID
        """
        if conversation_id in self.conversations:
            conversation = self.conversations[conversation_id]
            conversation.is_compromised = True
            logger.warning(f"标记对话为已被攻陷: {conversation_id}")
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话对象。
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            对话对象，如果不存在则返回None
        """
        return self.conversations.get(conversation_id)
    
    def add_user_message_to_conversation(self, conversation_id: str, content: str) -> None:
        """向指定对话添加用户消息。
        
        Args:
            conversation_id: 对话ID
            content: 用户消息内容
        """
        if conversation_id in self.conversations:
            self.conversations[conversation_id].add_message("user", content)
            logger.debug(f"向对话 {conversation_id} 添加用户消息")
        else:
            logger.warning(f"尝试向不存在的对话 {conversation_id} 添加消息")
    
    def _extract_conversation_id(self, request: InterceptedRequest) -> Optional[str]:
        """从请求中提取对话ID。"""
        # 可以从请求头或查询参数中提取
        if request.headers:
            conversation_id = request.headers.get("X-Conversation-ID")
            if conversation_id:
                return conversation_id
        
        # 尝试从查询参数中提取
        if request.query_params:
            conversation_id = request.query_params.get("conversation_id")
            if conversation_id:
                return conversation_id
        
        # 基于客户端IP生成稳定的对话ID（但需要考虑安全拦截后的清理）
        # 使用客户端IP作为基础，但当检测到安全威胁时需要重置
        if hasattr(request, 'client_ip') and request.client_ip:
            return f"client_{request.client_ip}"
        
        return None
    
    def _extract_model_from_request(self, request: InterceptedRequest) -> Optional[str]:
        """从请求中提取模型名称。"""
        if request.body and isinstance(request.body, dict):
            return request.body.get("model")
        return None
    
    def _extract_user_content(self, request: InterceptedRequest) -> str:
        """从请求中提取用户内容。"""
        if not request.body or not isinstance(request.body, dict):
            return ""
            
        content = ""
        
        # 从messages中提取内容
        if "messages" in request.body:
            for message in request.body["messages"]:
                if isinstance(message, dict) and message.get("role") == "user":
                    content += message.get("content", "") + "\n"
        
        # 从prompt中提取内容
        elif "prompt" in request.body:
            content = request.body["prompt"]
        
        # 从inputs中提取内容
        elif "inputs" in request.body:
            content = request.body["inputs"]
            
        return content.strip()
    
    def _extract_assistant_content(self, response: InterceptedResponse) -> str:
        """从响应中提取助手内容。"""
        if not response.body or not isinstance(response.body, dict):
            return ""
            
        content = ""
        
        # 从choices中提取内容
        if "choices" in response.body:
            for choice in response.body["choices"]:
                if isinstance(choice, dict):
                    if "message" in choice and "content" in choice["message"]:
                        content += choice["message"]["content"] + "\n"
                    elif "text" in choice:
                        content += choice["text"] + "\n"
        
        # 从completion中提取内容
        elif "completion" in response.body:
            content = response.body["completion"]
        
        # 从generated_text中提取内容
        elif "generated_text" in response.body:
            content = response.body["generated_text"]
            
        return content.strip()
    
    def _cleanup_old_conversations(self) -> None:
        """清理过期的对话。"""
        current_time = time.time()
        conversations_to_remove = []
        
        for conversation_id, conversation in self.conversations.items():
            # 如果对话超过最大时间或者对话数量超过限制
            if (current_time - conversation.updated_at > self.max_message_age or 
                len(self.conversations) > self.max_conversations):
                conversations_to_remove.append(conversation_id)
        
        for conversation_id in conversations_to_remove:
            del self.conversations[conversation_id]
            logger.debug(f"清理过期对话: {conversation_id}")


# 创建全局对话跟踪器实例
conversation_tracker = ConversationTracker()