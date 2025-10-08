# src/utils/token_manager.py
from ast import comprehension
from typing import List
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
)
import logging
import copy
import asyncio
from langchain_openai import ChatOpenAI
from src.config.loader import load_yaml_config

logger = logging.getLogger(__name__)


def get_search_config():
    config = load_yaml_config("conf.yaml")
    search_config = config.get("MODEL_TOKEN_LIMITS", {})
    return search_config
import json

class ContextManager:
    def __init__(self, llm, max_tokens=32768, prestore_messages_count: int = 2):
        self.llm = llm
        # 保存前几条消息，这是重要message，不能被删除
        self.prestore_messages_count = prestore_messages_count
        self.compress_count = 0           # 当前连续裁剪次数
        self.complete_summary_idx = 0           # 最近一次压缩的语义摘要索引
        self.max_tokens = max_tokens

    def _message_weight(self, message: BaseMessage) -> float:
        # 根据类型返回权重，值越大表示越“昂贵”（越容易被删）
        # 计算得到的token数量是大于真实的token数的，可以避免LLM调用时超出token限制
        if isinstance(message, AIMessage):
            return 1.2
        if isinstance(message, ToolMessage):
            return 1.5
        # System 和 Human 消息的权重设为 1.0
        return 1.0

    def _count_text_tokens(self, text: str) -> int:
        """
        Count tokens in text with different calculations for English and non-English characters.
        English characters: 4 characters ≈ 1 token
        Non-English characters (e.g., Chinese): 1 character ≈ 1 token

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        english_chars = 0
        non_english_chars = 0

        for char in text:
            # Check if character is ASCII (English letters, digits, punctuation)
            if ord(char) < 128:
                english_chars += 1
            else:
                non_english_chars += 1

        # Calculate tokens: English at 4 chars/token, others at 1 char/token
        english_tokens = english_chars // 4
        non_english_tokens = non_english_chars

        return english_tokens + non_english_tokens

    def count_tokens(self, messages: list[BaseMessage]) -> int:
        """
        获取上下文的token长度
        """
        total_length = 0
        for msg in messages:
            total_length += self._count_one_message(msg)
        return total_length
    
    def _count_one_message(self, message: BaseMessage) -> int:
        """
        计算一条消息的token长度
        """
        total_token = 0
        # Count tokens in content field
        if hasattr(message, "content") and message.content:
            total_token += self._count_text_tokens(message.content)
        
        if hasattr(message, "type") and message.type:
            total_token += self._count_text_tokens(message.type)
        
        total_token = int(total_token*self._message_weight(message))
        
        if hasattr(message,"additional_kwargs") and message.additional_kwargs:
            total_token += self._count_text_tokens(json.dumps(message.additional_kwargs, ensure_ascii=False))
            if "tool_calls" in message.additional_kwargs:
                total_token += 50  # Add estimation for function call information

        # Ensure at least 1 token
        return max(1, total_token)

    def is_over_limit(self, messages: list[BaseMessage]) -> bool:
        """
        判断上下文是否超出token限制
        """
        return self.count_tokens(messages) > self.max_tokens


    def compress_messages(self, messages: list) -> list:
        """
        压缩上下文
        """
        # 检查是否需要压缩
        if not self.is_over_limit(messages):
            return messages
        
        # 进行压缩
        compressed_messages = self._compress_messages(messages)

        logger.info(f"压缩前token长度: {self.count_tokens(messages)}")
        logger.info(f"压缩后token长度: {self.count_tokens(compressed_messages)}")
        
        return compressed_messages
    
    def _truncate_message_content(
        self, message: BaseMessage, max_tokens: int
    ) -> BaseMessage:
        """
        Truncate message content while preserving all other attributes by copying the original message
        and only modifying its content attribute.
        
        Args:
            message: The message to truncate
            max_tokens: Maximum number of tokens to keep

        Returns:
            New message instance with truncated content
        """

        # Create a deep copy of the original message to preserve all attributes
        truncated_message = copy.deepcopy(message)

        # Truncate only the content attribute
        truncated_message.content = message.content[:max_tokens]
        
        return truncated_message

    def _compress_messages(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """
        压缩上下文
        """
        available_token = self.max_tokens
        prefix_messages = []
        # 1.保留指定长度的头消息，以保留系统提示和用户输入
        for i in range(min(self.prestore_messages_count, len(messages))):
            cur_token_cnt = self._count_one_message(messages[i])
            if available_token > 0 and available_token >= cur_token_cnt:
                prefix_messages.append(messages[i])
                available_token -= cur_token_cnt
            elif available_token > 0:

                truncated_message = self._truncate_message_content(
                    messages[i], available_token
                )
                prefix_messages.append(truncated_message)
                return prefix_messages
            else:
                break
        # 2. 使用 语义压缩
        suffix_messages = self._semantic_summarize(messages[len(prefix_messages):])
        # 3. 合并前缀消息和压缩后的后缀消息
        compressed_messages = prefix_messages + suffix_messages

        return compressed_messages
    
    def _semantic_summarize(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """
        语义压缩上下文
        """
        # 使用异步方式并行处理
        return asyncio.run(self._async_semantic_summarize(messages))
    
    async def _async_semantic_summarize(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """
        异步语义压缩上下文
        """
        # 1. 过滤掉ToolMessage
        filtered_messages = [msg for msg in messages if not isinstance(msg, ToolMessage)]
        
        # 2. 按块处理Human/AI消息（2个对话/四个message为一块）
        processed_messages = []
        block_tasks = []  # 存储异步任务
        i = 0
        
        while i < len(filtered_messages):
            # 检查当前消息是否为HumanMessage或AIMessage
            if isinstance(filtered_messages[i], (HumanMessage, AIMessage)):
                # 获取当前对话块（最多4个消息：2个对话回合）
                block_messages = []
                j = i
                dialogue_count = 0
                
                while j < len(filtered_messages) and dialogue_count < 2:
                    current_msg = filtered_messages[j]
                    if isinstance(current_msg, (HumanMessage, AIMessage)):
                        block_messages.append(current_msg)
                        # 一个对话回合包含一个HumanMessage和一个AIMessage
                        if isinstance(current_msg, HumanMessage):
                            dialogue_count += 0.5
                        elif isinstance(current_msg, AIMessage):
                            dialogue_count += 0.5
                    else:
                        # 非Human/AI消息直接添加到结果中
                        processed_messages.append(current_msg)
                    j += 1
                
                # 如果收集到了有效的对话块，创建异步压缩任务
                if len(block_messages) >= 2:  # 至少有一个完整的对话回合
                    # 创建异步任务但不立即执行
                    block_tasks.append({
                        'block_messages': block_messages,
                        'position': len(processed_messages)  # 记录在结果列表中的位置
                    })
                    # 先添加占位符
                    processed_messages.append(None)
                else:
                    # 如果块太小，直接保留原消息
                    processed_messages.extend(block_messages)
                
                i = j  # 移动到下一个块
            else:
                # 非Human/AI消息直接保留
                processed_messages.append(filtered_messages[i])
                i += 1
        
        # 并行执行所有压缩任务
        if block_tasks:
            # 创建异步任务列表
            tasks = []
            for task_info in block_tasks:
                task = asyncio.create_task(
                    self._async_summarize_dialogue_block(task_info['block_messages'])
                )
                tasks.append((task_info['position'], task))
            
            # 等待所有任务完成
            for position, task in tasks:
                try:
                    summary_message = await task
                    processed_messages[position] = summary_message
                except Exception as e:
                    logger.error(f"异步语义压缩失败：{e}")
                    # 如果压缩失败，使用第一条消息作为占位符
                    block_messages = next((t['block_messages'] for t in block_tasks if t['position'] == position), [])
                    if block_messages:
                        processed_messages[position] = AIMessage(
                            content=f"[压缩失败] {block_messages[0].content[:100]}..."
                        )
        
        # 过滤掉None值（理论上不应该有，但为了安全）
        processed_messages = [msg for msg in processed_messages if msg is not None]
        
        logger.info(f"语义压缩完成：原始消息数 {len(messages)} -> 压缩后消息数 {len(processed_messages)}")
        return processed_messages
    
    async def _async_summarize_dialogue_block(self, block_messages: list[BaseMessage]) -> BaseMessage:
        """
        异步对对话块进行语义压缩
        """
        # 构建对话文本
        dialogue_text = ""
        for msg in block_messages:
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            dialogue_text += f"{role}: {msg.content}\n"
        
        # 使用LLM进行语义压缩
        prompt = f"""
        请对以下对话进行压缩总结，保留核心信息和对话要点，同时保持语义连贯性。
        对话内容：
        {dialogue_text}
        
        请用简洁的语言总结这段对话的主要内容。
        """
        
        try:
            # 异步调用LLM进行总结
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            summary_content = response.content if hasattr(response, 'content') else str(response)
            
            # 创建总结消息（使用AIMessage类型）
            summary_message = AIMessage(
                content=f"{summary_content}",
                additional_kwargs={"original_block_size": len(block_messages)}
            )
            
            logger.info(f"对话块压缩：{len(block_messages)}条消息 -> 1条总结消息")
            return summary_message
            
        except Exception as e:
            logger.error(f"语义压缩失败：{e}")
            # 如果压缩失败，返回第一条消息作为占位符
            return AIMessage(content=f"[压缩失败] {block_messages[0].content[:100]}...")
        
