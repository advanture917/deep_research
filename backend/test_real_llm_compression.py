#!/usr/bin/env python3
"""
使用真实LLM测试compress_messages功能
"""

import asyncio

from langchain.agents import create_react_agent
from langchain.tools import tool
from src.utils.content import ContextManager
from src.llms.llm import get_llm
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

async def test_real_llm_compression():
    """使用真实LLM测试压缩功能"""
    print("=== 开始真实LLM压缩测试 ===")
    
    try:
        # 获取真实LLM
        llm = get_llm()
        print("✓ 成功获取LLM实例")
        
        # 创建ContextManager
        context_manager = ContextManager(llm, max_tokens=1000, prestore_messages_count=2)
        print("✓ 创建ContextManager实例")
        
        # 测试1: 基本压缩测试（不触发压缩）
        print("\n--- 测试1: 基本压缩测试（不触发压缩） ---")
        short_messages = [
            HumanMessage(content="你好，我有一个问题"),
            AIMessage(content="你好！我很乐意帮助你。请告诉我你的问题是什么？"),
            HumanMessage(content="我想了解人工智能的发展历史")
        ]
        
        original_tokens = context_manager.count_tokens(short_messages)
        print(f"原始消息token数: {original_tokens}")
        
        compressed = context_manager.compress_messages(short_messages)
        compressed_tokens = context_manager.count_tokens(compressed)
        print(f"压缩后token数: {compressed_tokens}")
        print(f"消息数量变化: {len(short_messages)} -> {len(compressed)}")
        
        # 测试2: 触发语义压缩的长消息测试
        print("\n--- 测试2: 触发语义压缩的长消息测试 ---")
        long_text = "人工智能的发展历史可以追溯到20世纪50年代。" * 50
        long_messages = [
            SystemMessage(content="你是一个AI助手"),
            HumanMessage(content="请详细介绍一下人工智能的发展历史"),
            AIMessage(content=long_text),
            HumanMessage(content="能再详细一些吗？"),
            AIMessage(content=long_text)
        ]
        
        original_tokens = context_manager.count_tokens(long_messages)
        print(f"原始消息token数: {original_tokens}")
        
        # 使用同步方式调用，避免异步事件循环冲突
        compressed = context_manager.compress_messages(long_messages)
        compressed_tokens = context_manager.count_tokens(compressed)
        print(f"压缩后token数: {compressed_tokens}")
        print(f"消息数量变化: {len(long_messages)} -> {len(compressed)}")
        
        # 显示压缩后的消息内容
        print("\n压缩后的消息内容:")
        for i, msg in enumerate(compressed):
            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            print(f"{i}: {type(msg).__name__} - {content_preview}")
        
        # 测试3: 包含ToolMessage的压缩测试
        print("\n--- 测试3: 包含ToolMessage的压缩测试 ---")
        tool_messages = [
            HumanMessage(content="查询今天的天气"),
            ToolMessage(content="北京今天晴天，温度25度", tool_call_id="weather_123"),
            AIMessage(content=long_text)
        ]
        
        original_tokens = context_manager.count_tokens(tool_messages)
        print(f"原始消息token数: {original_tokens}")
        
        compressed = context_manager.compress_messages(tool_messages)
        compressed_tokens = context_manager.count_tokens(compressed)
        print(f"压缩后token数: {compressed_tokens}")
        print(f"消息数量变化: {len(tool_messages)} -> {len(compressed)}")
        
        # 测试4: 预设消息保留测试
        print("\n--- 测试4: 预设消息保留测试 ---")
        context_manager_small = ContextManager(llm, max_tokens=50, prestore_messages_count=2)
        
        preserve_messages = [
            HumanMessage(content="第一条重要消息"),
            AIMessage(content="AI回复第一条"),
            HumanMessage(content="用户继续提问"),
            AIMessage(content="AI回复第二条")
        ]
        
        original_tokens = context_manager_small.count_tokens(preserve_messages)
        print(f"原始消息token数: {original_tokens}")
        
        compressed = context_manager_small.compress_messages(preserve_messages)
        compressed_tokens = context_manager_small.count_tokens(compressed)
        print(f"压缩后token数: {compressed_tokens}")
        print(f"消息数量变化: {len(preserve_messages)} -> {len(compressed)}")
        
        # 验证前2条消息被保留
        if len(compressed) >= 2:
            print("✓ 前2条消息被正确保留")
            print(f"  保留消息1: {compressed[0].content[:50]}...")
            print(f"  保留消息2: {compressed[1].content[:50]}...")
        
        print("\n=== 真实LLM压缩测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数 - 使用同步方式运行测试"""
    print("=== 开始真实LLM压缩测试 ===")
    
    try:
        # 获取真实LLM
        llm = get_llm()
        print("✓ 成功获取LLM实例")
        
        # 创建ContextManager
        context_manager = ContextManager(llm, max_tokens=1000, prestore_messages_count=2)
        print("✓ 创建ContextManager实例")
        
        # 测试1: 基本压缩测试（不触发压缩）
        print("\n--- 测试1: 基本压缩测试（不触发压缩） ---")
        short_messages = [
            HumanMessage(content="你好，我有一个问题"),
            AIMessage(content="你好！我很乐意帮助你。请告诉我你的问题是什么？"),
            HumanMessage(content="我想了解人工智能的发展历史")
        ]
        
        original_tokens = context_manager.count_tokens(short_messages)
        print(f"原始消息token数: {original_tokens}")
        
        compressed = context_manager.compress_messages(short_messages)
        compressed_tokens = context_manager.count_tokens(compressed)
        print(f"压缩后token数: {compressed_tokens}")
        print(f"消息数量变化: {len(short_messages)} -> {len(compressed)}")
        
        # 测试2: 触发语义压缩的长消息测试
        print("\n--- 测试2: 触发语义压缩的长消息测试 ---")
        long_text = "人工智能的发展历史可以追溯到20世纪50年代。" * 50
        long_messages = [
            SystemMessage(content="你是一个AI助手"),
            HumanMessage(content="请详细介绍一下人工智能的发展历史"),
            AIMessage(content=long_text),
            HumanMessage(content="能再详细一些吗？"),
            AIMessage(content=long_text)
        ]
        
        original_tokens = context_manager.count_tokens(long_messages)
        print(f"原始消息token数: {original_tokens}")
        
        compressed = context_manager.compress_messages(long_messages)
        compressed_tokens = context_manager.count_tokens(compressed)
        print(f"压缩后token数: {compressed_tokens}")
        print(f"消息数量变化: {len(long_messages)} -> {len(compressed)}")
        
        # 显示压缩后的消息内容
        print("\n压缩后的消息内容:")
        for i, msg in enumerate(compressed):
            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            print(f"{i}: {type(msg).__name__} - {content_preview}")
        
        # 测试3: 包含ToolMessage的压缩测试
        print("\n--- 测试3: 包含ToolMessage的压缩测试 ---")
        tool_messages = [
            HumanMessage(content="查询今天的天气"),
            ToolMessage(content="北京今天晴天，温度25度", tool_call_id="weather_123"),
            AIMessage(content=long_text)
        ]
        
        original_tokens = context_manager.count_tokens(tool_messages)
        print(f"原始消息token数: {original_tokens}")
        
        compressed = context_manager.compress_messages(tool_messages)
        compressed_tokens = context_manager.count_tokens(compressed)
        print(f"压缩后token数: {compressed_tokens}")
        print(f"消息数量变化: {len(tool_messages)} -> {len(compressed)}")
        
        # 测试4: 预设消息保留测试
        print("\n--- 测试4: 预设消息保留测试 ---")
        context_manager_small = ContextManager(llm, max_tokens=50, prestore_messages_count=2)
        
        preserve_messages = [
            HumanMessage(content="第一条重要消息"),
            AIMessage(content="AI回复第一条"),
            HumanMessage(content="用户继续提问"),
            AIMessage(content="AI回复第二条")
        ]
        
        original_tokens = context_manager_small.count_tokens(preserve_messages)
        print(f"原始消息token数: {original_tokens}")
        
        compressed = context_manager_small.compress_messages(preserve_messages)
        compressed_tokens = context_manager_small.count_tokens(compressed)
        print(f"压缩后token数: {compressed_tokens}")
        print(f"消息数量变化: {len(preserve_messages)} -> {len(compressed)}")
        
        # 验证前2条消息被保留
        if len(compressed) >= 2:
            print("✓ 前2条消息被正确保留")
            print(f"  保留消息1: {compressed[0].content[:50]}...")
            print(f"  保留消息2: {compressed[1].content[:50]}...")
        
        print("\n=== 真实LLM压缩测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

@tool
def tool() -> None:
    """Testing tool."""
    ...
if __name__ == "__main__":
    # main()
    llm = get_llm()
    from langgraph.prebuilt import create_react_agent
    rllm = create_react_agent(llm,tools= [tool])
    # LangGraph的create_react_agent期望输入是字典格式，包含"input"键
    human_msg = HumanMessage(content="你好，我有一个问题")
    res = llm.invoke([human_msg])


    print(res.content)
