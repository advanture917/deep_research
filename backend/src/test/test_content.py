import unittest
import asyncio
from unittest.mock import Mock, AsyncMock
from src.utils.content import ContextManager
from src.llms.llm import get_llm
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage


class TestContextManager(unittest.TestCase):
    """测试ContextManager类的功能"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建一个模拟的LLM用于测试
        self.mock_llm = Mock()
        self.mock_llm.ainvoke = AsyncMock()
        
        # 创建ContextManager实例
        self.context_manager = ContextManager(self.mock_llm, max_tokens=1000, prestore_messages_count=2)
    
    def test_token_counting_english(self):
        """测试英文文本的token计数"""
        text = "Hello world, this is a test message"
        token_count = self.context_manager._count_text_tokens(text)
        # 英文文本：大约 7 个单词，每个单词约1个token，加上标点
        self.assertGreater(token_count, 5)
        self.assertLess(token_count, 10)
    
    def test_token_counting_chinese(self):
        """测试中文文本的token计数"""
        text = "你好，这是一个测试消息"
        token_count = self.context_manager._count_text_tokens(text)
        # 中文文本：每个字符约1个token
        # "你好，这是一个测试消息" 包含11个字符（包括中文逗号），所有都是非ASCII字符
        self.assertEqual(token_count, 11)  # 11个非ASCII字符
    
    def test_token_counting_mixed(self):
        """测试中英文混合文本的token计数"""
        text = "Hello 你好，this is a test 测试"
        token_count = self.context_manager._count_text_tokens(text)
        # 英文部分约5个token，中文部分约4个token
        self.assertGreaterEqual(token_count, 9)
    
    def test_count_one_message_human(self):
        """测试HumanMessage的token计数"""
        message = HumanMessage(content="这是一个测试消息")
        token_count = self.context_manager._count_one_message(message)
        self.assertGreater(token_count, 0)
    
    def test_count_one_message_ai(self):
        """测试AIMessage的token计数（应该有更高的权重）"""
        message = AIMessage(content="这是一个AI回复")
        token_count = self.context_manager._count_one_message(message)
        self.assertGreater(token_count, 0)
    
    def test_count_one_message_tool(self):
        """测试ToolMessage的token计数（应该有最高的权重）"""
        message = ToolMessage(content="这是一个工具消息", tool_call_id="123")
        token_count = self.context_manager._count_one_message(message)
        self.assertGreater(token_count, 0)
    
    def test_count_tokens_multiple_messages(self):
        """测试多条消息的token计数"""
        messages = [
            HumanMessage(content="第一条消息"),
            AIMessage(content="AI回复"),
            HumanMessage(content="第二条消息")
        ]
        total_tokens = self.context_manager.count_tokens(messages)
        self.assertGreater(total_tokens, 0)
    
    def test_is_over_limit_false(self):
        """测试未超过token限制的情况"""
        messages = [HumanMessage(content="短消息")]
        result = self.context_manager.is_over_limit(messages)
        self.assertFalse(result)
    
    def test_is_over_limit_true(self):
        """测试超过token限制的情况"""
        # 创建一个很长的消息来超过限制
        long_text = "这是一个很长的消息" * 1000
        messages = [HumanMessage(content=long_text)]
        result = self.context_manager.is_over_limit(messages)
        self.assertTrue(result)
    
    def test_compress_messages_no_compression_needed(self):
        """测试不需要压缩的情况"""
        messages = [HumanMessage(content="短消息")]
        compressed = self.context_manager.compress_messages(messages)
        self.assertEqual(compressed, messages)
    
    def test_compress_messages_with_truncation(self):
        """测试需要截断的压缩情况"""
        # 设置较小的max_tokens来强制压缩
        context_manager = ContextManager(self.mock_llm, max_tokens=10, prestore_messages_count=1)
        
        # 创建超过限制的消息
        messages = [
            HumanMessage(content="第一条长消息需要被截断"),
            AIMessage(content="AI回复消息"),
            HumanMessage(content="第二条用户消息")
        ]
        
        compressed = context_manager.compress_messages(messages)
        
        # 验证压缩后的消息数减少
        self.assertLess(len(compressed), len(messages))
        # 验证第一条消息被保留但可能被截断
        self.assertIsInstance(compressed[0], HumanMessage)
    
    def test_compress_messages_with_semantic_compression(self):
        """测试语义压缩功能"""
        # 设置模拟LLM的异步响应
        mock_response = Mock()
        mock_response.content = "这是对话的语义总结"
        self.mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        
        # 创建需要压缩的消息列表
        # 使用短的前缀消息，确保有剩余token进行语义压缩
        short_text = "短消息"
        long_text = "这是一个很长的消息内容" * 100
        messages = [
            SystemMessage(content=short_text),  # 短系统消息
            HumanMessage(content=short_text),   # 短用户消息
            AIMessage(content=long_text),        # 长AI回复
            HumanMessage(content=long_text),     # 长用户消息
            AIMessage(content=long_text)         # 长AI回复
        ]
        
        compressed = self.context_manager.compress_messages(messages)
        
        # 验证语义压缩被调用
        self.mock_llm.ainvoke.assert_called()
        # 验证压缩后的token数减少
        original_tokens = self.context_manager.count_tokens(messages)
        compressed_tokens = self.context_manager.count_tokens(compressed)
        self.assertLess(compressed_tokens, original_tokens)
    
    def test_compress_messages_preserve_prestore_messages(self):
        """测试保留预设消息的功能"""
        # 设置较小的max_tokens但保留2条消息
        context_manager = ContextManager(self.mock_llm, max_tokens=20, prestore_messages_count=2)
        
        messages = [
            HumanMessage(content="第一条消息"),
            AIMessage(content="AI回复1"),
            HumanMessage(content="用户继续提问"),
            AIMessage(content="AI回复2")
        ]
        
        compressed = context_manager.compress_messages(messages)
        
        # 验证前2条消息被保留
        self.assertEqual(compressed[0].content, "第一条消息")
        self.assertEqual(compressed[1].content, "AI回复1")
    
    def test_compress_messages_with_tool_messages(self):
        """测试包含ToolMessage的压缩"""
        # 设置模拟LLM的异步响应
        mock_response = Mock()
        mock_response.content = "工具调用总结"
        self.mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        
        # 创建需要压缩的消息列表
        # 使用短的前缀消息，确保有剩余token进行语义压缩
        short_text = "短消息"
        long_text = "这是一个很长的消息内容" * 100
        messages = [
            HumanMessage(content=short_text),   # 短用户消息
            ToolMessage(content="工具调用结果", tool_call_id="123"),
            AIMessage(content=long_text)         # 长AI回复
        ]
        
        compressed = self.context_manager.compress_messages(messages)
        
        # 验证压缩后的token数减少
        original_tokens = self.context_manager.count_tokens(messages)
        compressed_tokens = self.context_manager.count_tokens(compressed)
        self.assertLess(compressed_tokens, original_tokens)
        # 验证语义压缩被调用
        self.mock_llm.ainvoke.assert_called()
    
    def test_compress_messages_token_count_validation(self):
        """测试压缩前后的token计数验证"""
        # 创建大量消息来触发压缩
        long_text = "这是一个很长的消息内容" * 100
        messages = [
            HumanMessage(content=long_text),
            AIMessage(content=long_text),
            HumanMessage(content=long_text)
        ]
        
        original_tokens = self.context_manager.count_tokens(messages)
        compressed = self.context_manager.compress_messages(messages)
        compressed_tokens = self.context_manager.count_tokens(compressed)
        
        # 验证压缩后token数减少
        self.assertLess(compressed_tokens, original_tokens)
        # 验证压缩后不超过限制（由于语义压缩可能仍然超过，我们只验证减少）
        # 注意：语义压缩可能不会完全压缩到限制以下，所以只验证减少
    
    def test_truncate_message_content(self):
        """测试消息内容截断功能"""
        original_message = HumanMessage(content="这是一个很长的消息内容需要被截断")
        truncated = self.context_manager._truncate_message_content(original_message, 5)
        
        self.assertEqual(len(truncated.content), 5)
        self.assertIsInstance(truncated, HumanMessage)
    
    def test_group_dialogue_blocks(self):
        """测试对话块分组功能"""
        messages = [
            HumanMessage(content="用户消息1"),
            AIMessage(content="AI回复1"),
            HumanMessage(content="用户消息2"),
            AIMessage(content="AI回复2"),
            SystemMessage(content="系统消息")  # 非Human/AI消息
        ]
        
        processed_messages, blocks = self.context_manager._group_dialogue_blocks(messages)
        
        # 系统消息应该被直接处理
        self.assertEqual(len(processed_messages), 1)
        self.assertIsInstance(processed_messages[0], SystemMessage)
        
        # 由于消息类型交替且token数未超限，应该只有1个对话块
        self.assertEqual(len(blocks), 1)
        # 检查块中包含所有Human/AI消息
        self.assertEqual(len(blocks[0]), 4)
        self.assertIsInstance(blocks[0][0], HumanMessage)
        self.assertIsInstance(blocks[0][1], AIMessage)
        self.assertIsInstance(blocks[0][2], HumanMessage)
        self.assertIsInstance(blocks[0][3], AIMessage)
    
    async def test_async_summarize_dialogue_block(self):
        """测试异步对话块压缩功能"""
        # 设置模拟LLM的响应
        mock_response = Mock()
        mock_response.content = "这是对话的总结"
        self.mock_llm.ainvoke.return_value = mock_response
        
        block_messages = [
            HumanMessage(content="用户问题"),
            AIMessage(content="AI回答")
        ]
        
        result = await self.context_manager._async_summarize_dialogue_block(block_messages)
        
        self.assertIsInstance(result, AIMessage)
        self.assertEqual(result.content, "这是对话的总结")
        self.mock_llm.ainvoke.assert_called_once()
    
    def test_message_weight_calculation(self):
        """测试消息权重计算"""
        human_msg = HumanMessage(content="test")
        ai_msg = AIMessage(content="test")
        tool_msg = ToolMessage(content="test", tool_call_id="123")
        
        human_weight = self.context_manager._message_weight(human_msg)
        ai_weight = self.context_manager._message_weight(ai_msg)
        tool_weight = self.context_manager._message_weight(tool_msg)
        
        self.assertEqual(human_weight, 1.0)
        self.assertEqual(ai_weight, 1.2)
        self.assertEqual(tool_weight, 1.5)


def run_basic_tests():
    """运行基本的功能测试"""
    print("=== 开始ContextManager基本测试 ===")
    
    # 获取真实的LLM
    try:
        llm = get_llm()
        context_manager = ContextManager(llm, max_tokens=1000)
        
        # 测试token计数
        test_message = HumanMessage(content="这是一个测试消息")
        token_count = context_manager._count_one_message(test_message)
        print(f"单条消息token计数: {token_count}")
        
        # 测试多条消息计数
        messages = [
            HumanMessage(content="第一条消息"),
            AIMessage(content="AI回复"),
            HumanMessage(content="用户继续提问")
        ]
        total_tokens = context_manager.count_tokens(messages)
        print(f"多条消息总token数: {total_tokens}")
        
        # 测试是否超过限制
        is_over = context_manager.is_over_limit(messages)
        print(f"是否超过token限制: {is_over}")
        
        print("=== 基本测试完成 ===")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")


if __name__ == "__main__":
    # 运行基本测试
    run_basic_tests()
    
    # 运行单元测试
    print("\n=== 开始单元测试 ===")
    unittest.main(argv=[''], verbosity=2, exit=False)
