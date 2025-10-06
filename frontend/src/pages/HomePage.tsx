import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useResearch } from '../context/ResearchContext';
import { ArrowRight, Sparkles, Brain, Target } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const HomePage: React.FC = () => {
  const { dispatch } = useResearch();
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    setIsLoading(true);
    
    try {
      // 调用后端API创建研究计划
      const response = await fetch('http://localhost:8000/api/research/create-plan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ topic: inputValue }),
      });

      if (response.ok) {
        const plan = await response.json();
        
        // 设置研究主题和计划
        dispatch({ type: 'SET_TOPIC', payload: inputValue });
        dispatch({ type: 'SET_PLAN', payload: plan });
        
        // 添加用户消息
        dispatch({
          type: 'ADD_MESSAGE',
          payload: {
            id: Date.now().toString(),
            role: 'user',
            content: inputValue,
            timestamp: new Date(),
          },
        });

        // 添加AI回复
        dispatch({
          type: 'ADD_MESSAGE',
          payload: {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `好的！我已经为您制定了关于"${inputValue}"的研究计划，包含${plan.steps.length}个研究步骤。`,
            timestamp: new Date(),
          },
        });

        setIsLoading(false);
        navigate('/plan');
      } else {
        throw new Error('创建研究计划失败');
      }
    } catch (error) {
      console.error('创建研究计划失败:', error);
      setIsLoading(false);
      alert('创建研究计划失败，请稍后重试');
    }
  };

  const sampleQuestions = [
    "2025年token2049大会有哪些重要议题和演讲？",
    "人工智能在医疗领域的最新发展趋势是什么？",
    "量子计算技术的商业化应用前景如何？",
    "可持续能源技术的投资热点分析",
  ];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center mb-12"
      >
        <div className="flex justify-center mb-6">
          <motion.div
            animate={{ rotate: [0, 10, -10, 0] }}
            transition={{ duration: 2, repeat: Infinity, repeatType: "reverse" }}
          >
            <Brain className="h-16 w-16 text-primary-500 mx-auto" />
          </motion.div>
        </div>
        <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-4">
          AI驱动的
          <span className="text-gradient">深度研究</span>
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          智能分析、深度挖掘、专业报告 - 让AI成为您的研究助手
        </p>
      </motion.div>

      {/* Input Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 card-shadow mb-8"
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="research-topic" className="block text-lg font-medium text-gray-700 mb-3">
              请输入您想要研究的主题或问题
            </label>
            <textarea
              id="research-topic"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="例如：2025年token2049大会有哪些重要议题和演讲？"
              className="input-field min-h-[120px] text-lg"
              disabled={isLoading}
            />
          </div>
          
          <motion.button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className={`w-full py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-200 ${
              isLoading || !inputValue.trim()
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'btn-primary'
            }`}
          >
            {isLoading ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="loading-spinner"></div>
                <span>正在分析...</span>
              </div>
            ) : (
              <div className="flex items-center justify-center space-x-2">
                <Sparkles className="h-5 w-5" />
                <span>开始深度研究</span>
              </div>
            )}
          </motion.button>
        </form>
      </motion.div>

      {/* Sample Questions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        className="bg-white/60 backdrop-blur-sm rounded-xl p-6"
      >
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <Sparkles className="h-5 w-5 text-accent-500 mr-2" />
          热门研究主题
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {sampleQuestions.map((question, index) => (
            <motion.button
              key={index}
              onClick={() => setInputValue(question)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="text-left p-4 bg-gray-50 hover:bg-primary-50 rounded-lg border border-gray-200 hover:border-primary-200 transition-all duration-200 text-sm text-gray-700 hover:text-primary-700"
            >
              {question}
            </motion.button>
          ))}
        </div>
      </motion.div>
    </div>
  );
};

export default HomePage;