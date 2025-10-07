# src/utils/token_manager.py
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
from langchain_openai import ChatOpenAI
from src.config.loader import load_yaml_config

logger = logging.getLogger(__name__)


def get_search_config():
    config = load_yaml_config("conf.yaml")
    search_config = config.get("MODEL_TOKEN_LIMITS", {})
    return search_config
import json

class ContextManager:
    def __init__(self, llm, max_tokens=32768):
        self.llm = llm
        self.max_tokens = max_tokens

    def compress(self, messages: list) -> list:
        """
        压缩上下文：将历史对话语义总结为简短版本
        """
        if self._token_length(messages) < self.max_tokens:
            return messages
        
        # 用LLM生成总结
        from langchain_core.messages import SystemMessage, HumanMessage
        summary_prompt = [
            SystemMessage(content="你是研究助手，请将以下历史对话压缩为语义摘要，保留关键信息。"),
            HumanMessage(content=self._concat(messages))
        ]
        summary = self.llm.invoke(summary_prompt)
        return [{"role": "system", "content": "摘要上下文：" + summary.content}]
    
    def summarize(self, step_results: list) -> str:
        """
        根据所有步骤的结果生成整体报告
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        summary_prompt = [
            SystemMessage(content="你是学术研究总结专家，请基于以下步骤结果生成连贯的研究报告。"),
            HumanMessage(content=json.dumps(step_results, ensure_ascii=False))
        ]
        result = self.llm.invoke(summary_prompt)
        return result.content
    
    def _token_length(self, messages):
        # 处理 LangChain 消息对象和普通字典
        total_length = 0
        for m in messages:
            if hasattr(m, 'content'):  # LangChain 消息对象
                total_length += len(m.content)
            elif isinstance(m, dict) and 'content' in m:  # 普通字典
                total_length += len(m["content"])
            else:
                # 如果无法获取内容，跳过或记录警告
                logger.warning(f"无法计算消息的token长度: {type(m)}")
        return total_length
    
    def _concat(self, messages):
        # 处理 LangChain 消息对象和普通字典
        parts = []
        for m in messages:
            if hasattr(m, 'content') and hasattr(m, 'type'):  # LangChain 消息对象
                role = m.type if hasattr(m, 'type') else 'unknown'
                content = m.content
            elif isinstance(m, dict) and 'content' in m and 'role' in m:  # 普通字典
                role = m['role']
                content = m['content']
            else:
                # 如果无法解析，跳过或记录警告
                logger.warning(f"无法解析消息: {type(m)}")
                continue
            parts.append(f"{role}: {content}")
        return "\n".join(parts)

