import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useResearch } from '../context/ResearchContext';
import { Sparkles, Brain, Radio, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { useNavigate } from 'react-router-dom';
import ChatInterface from '../components/ChatInterface';
import { useResearchStream } from '../hooks/useResearchStream';
import { startResearch } from '../services/researchService';

const HomePage: React.FC = () => {
  const { state, dispatch } = useResearch();
  const [isLoading, setIsLoading] = useState(false);
  const [currentPlanId, setCurrentPlanId] = useState<string | null>(null);
  const navigate = useNavigate();
  
  // 使用研究流Hook
  const { state: streamState, isLoading: streamLoading, error: streamError, isConnected } = useResearchStream(currentPlanId);

  // 处理发送消息 - 使用LangGraph实时流
  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return;

    setIsLoading(true);
    
    // 添加用户消息
    dispatch({
      type: 'ADD_MESSAGE',
      payload: {
        id: Date.now().toString(),
        role: 'user',
        content: message,
        timestamp: new Date(),
      },
    });

    try {
      // 使用研究服务开始研究流程
      const result = await startResearch(message, 'zh-CN');
      
      // 只有当问题需要研究计划时才启动实时流轮询
      if (result.need_plan) {
        setCurrentPlanId(result.plan_id || null);
      }
      
      // 更新研究上下文状态
      dispatch({
        type: 'UPDATE_FROM_BACKEND',
        payload: {
          researchTopic: message,
          planId: result.plan_id,
          status: result.status,
          currentStage: result.current_stage,
          needPlan: result.need_plan,
          researchSummary: result.research_summary,
          stepResults: result.step_results || [],
        },
      });

      // 添加AI初始回复
      dispatch({
        type: 'ADD_MESSAGE',
        payload: {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: typeof result.messages === 'string' ? result.messages : `好的！我已经开始为您研究关于"${message}"的相关内容。`,
          timestamp: new Date(),
        },
      });

    } catch (error) {
      console.error('开始研究失败:', error);
      
      // 添加错误消息
      dispatch({
        type: 'ADD_MESSAGE',
        payload: {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: '抱歉，处理您的请求时出现了问题。请稍后重试。',
          timestamp: new Date(),
        },
      });
    } finally {
      setIsLoading(false);
    }
  };

  // 监听实时流状态变化
  useEffect(() => {
    if (streamState) {
      // 添加调试日志
      console.log('🔄 实时流状态更新:', {
        status: streamState.status,
        need_plan: streamState.need_plan,
        current_stage: streamState.current_stage,
        has_plan: !!streamState.current_plan,
        messages: streamState.messages
      });

      // 如果后端返回了消息内容，添加到消息列表
      if (streamState.messages && typeof streamState.messages === 'string') {
        dispatch({
          type: 'ADD_MESSAGE',
          payload: {
            id: Date.now().toString(),
            role: 'assistant',
            content: streamState.messages,
            timestamp: new Date(),
          },
        });
      }
      
      // 更新研究上下文状态
      dispatch({
        type: 'UPDATE_FROM_BACKEND',
        payload: {
          status: streamState.status,
          currentStage: streamState.current_stage,
          needPlan: streamState.need_plan,
          currentPlan: streamState.current_plan,
          researchSummary: streamState.research_summary,
          stepResults: streamState.step_results || [],
        },
      });

      // 根据状态变化处理导航 - 添加更详细的条件判断
      const shouldNavigateToPlan = streamState.need_plan && 
        (streamState.status === 'awaiting_confirmation' || streamState.status === 'plan_generated');
      
      console.log('🧭 导航判断:', {
        shouldNavigateToPlan,
        condition1: streamState.need_plan,
        condition2: streamState.status === 'awaiting_confirmation' || streamState.status === 'plan_generated',
        status: streamState.status
      });

      if (shouldNavigateToPlan) {
        console.log('🚀 导航到计划页面');
        // 需要用户确认计划，导航到计划页面并停止轮询
        setCurrentPlanId(null); // 停止实时流轮询，让计划页面处理后续交互
        navigate('/plan');
      } else if (streamState.status === 'completed') {
        console.log('🚀 导航到报告页面');
        // 研究完成，导航到报告页面并停止实时流轮询
        setCurrentPlanId(null); // 停止实时流轮询
        navigate('/report');
      }
    }
  }, [streamState, dispatch, navigate]);

  // 监听流错误
  useEffect(() => {
    if (streamError) {
      console.error('研究流错误:', streamError);
      // 可以在这里添加错误处理逻辑
    }
  }, [streamError]);

  const sampleQuestions = [
    "2025年token2049大会有哪些重要议题和演讲？",
    "人工智能在医疗领域的最新发展趋势是什么？",
    "量子计算技术的商业化应用前景如何？",
    "可持续能源技术的投资热点分析",
  ];

  // 过滤掉system角色的消息，只显示user和assistant角色的消息，并进行类型转换
  const filteredMessages = state.messages
    .filter(msg => msg.role === 'user' || msg.role === 'assistant')
    .map(msg => ({
      id: msg.id,
      role: msg.role as 'user' | 'assistant',
      content: msg.content,
      timestamp: msg.timestamp
    }));
  
  // 组合加载状态
  const combinedIsLoading = isLoading || streamLoading;

  // 生成研究报告
  const generateReport = () => {
    if (state.status === 'completed' && state.researchSummary) {
      // 直接使用后端返回的researchSummary内容
      return {
        title: `关于"${state.researchTopic}"的研究报告`,
        content: state.researchSummary, // 直接使用后端生成的Markdown内容
        created_at: new Date().toISOString(),
      };
    }
    return null;
  };

  const report = generateReport();
  
  return (
    <div className="h-screen flex flex-col">
      {/* 实时流状态栏 */}
      <div className="bg-gray-50 border-b border-gray-200 px-4 py-2">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-2">
            <Radio className={`h-3 w-3 ${isConnected ? 'text-green-500' : 'text-gray-400'}`} />
            <span className="text-gray-600">
              LangGraph实时流: {isConnected ? '已连接' : '待连接'}
            </span>
            {streamState && (
              <span className="text-gray-500">
                | 状态: {streamState.status} | 阶段: {streamState.current_stage || '等待中'}
              </span>
            )}
          </div>
          {currentPlanId && (
            <span className="text-gray-400 text-xs">计划ID: {currentPlanId}</span>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
      
      {/* 欢迎区域 - 仅在消息为空时显示 */}
      {state.messages.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center py-8"
        >
          <div className="flex justify-center mb-4">
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity, repeatType: "reverse" }}
            >
              <Brain className="h-12 w-12 text-primary-500 mx-auto" />
            </motion.div>
          </div>
          <h1 className="text-2xl md:text-4xl font-bold text-gray-900 mb-2">
            AI驱动的
            <span className="text-gradient">深度研究</span>
          </h1>
          <p className="text-lg text-gray-600 mb-6 max-w-2xl mx-auto">
            智能分析、深度挖掘、专业报告 - 让AI成为您的研究助手
          </p>
          
          {/* Sample Questions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="bg-white/60 backdrop-blur-sm rounded-xl p-4 mx-4 mb-4"
          >
            <h3 className="text-md font-semibold text-gray-800 mb-3 flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-accent-500 mr-2" />
              热门研究主题
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {sampleQuestions.map((question, index) => (
                <motion.button
                  key={index}
                  onClick={() => handleSendMessage(question)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="text-left p-3 bg-gray-50 hover:bg-primary-50 rounded-lg border border-gray-200 hover:border-primary-200 transition-all duration-200 text-sm text-gray-700 hover:text-primary-700"
                >
                  {question}
                </motion.button>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
      
        {/* 聊天界面 - 始终显示 */}
        <div className="flex-1 overflow-hidden">
          <ChatInterface
            messages={filteredMessages}
            onSendMessage={handleSendMessage}
            isLoading={combinedIsLoading}
            placeholder="请输入您的问题或研究主题..."
          />
        </div>

        {/* 研究报告展示区域 - 当研究完成时显示 */}
        {report && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="bg-white border-t border-gray-200 max-h-80 overflow-y-auto flex-shrink-0"
          >
            <div className="max-w-4xl mx-auto p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <FileText className="h-5 w-5 text-primary-500" />
                  <h3 className="text-lg font-semibold text-gray-800">研究报告</h3>
                </div>
                <button
                  onClick={() => navigate('/report')}
                  className="text-sm text-primary-600 hover:text-primary-700 underline"
                >
                  查看完整报告 →
                </button>
              </div>
              
              <div className="prose prose-sm max-w-none bg-gray-50 rounded-lg p-4 max-h-48 overflow-y-auto">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw]}
                  components={{
                    h1: ({ children }) => <h1 className="text-xl font-bold text-gray-900 mb-3">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-lg font-bold text-gray-800 mb-2 mt-4">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-base font-semibold text-gray-800 mb-2 mt-3">{children}</h3>,
                    p: ({ children }) => <p className="text-gray-700 leading-relaxed mb-2 text-sm">{children}</p>,
                    ul: ({ children }) => <ul className="list-disc list-inside text-gray-700 mb-2 space-y-1 text-sm">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal list-inside text-gray-700 mb-2 space-y-1 text-sm">{children}</ol>,
                    li: ({ children }) => <li className="text-gray-700 text-sm">{children}</li>,
                    blockquote: ({ children }) => <blockquote className="border-l-3 border-primary-400 pl-3 italic text-gray-600 my-2 text-sm">{children}</blockquote>,
                    code: ({ children, ...props }) => 
                      props.className?.includes('language') ? 
                        <code className="block bg-gray-100 p-2 rounded text-xs font-mono overflow-x-auto my-2">{children}</code> :
                        <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono">{children}</code>,
                    pre: ({ children }) => <pre className="bg-gray-100 p-2 rounded overflow-x-auto my-2 text-xs">{children}</pre>,
                    strong: ({ children }) => <strong className="font-bold text-gray-900">{children}</strong>,
                    em: ({ children }) => <em className="italic text-gray-700">{children}</em>,
                  }}
                >
                  {report.content}
                </ReactMarkdown>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default HomePage;