import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useResearch } from '../context/ResearchContext';
import { Play, Pause, Square, CheckCircle, Clock, AlertCircle, RefreshCw, Radio } from 'lucide-react';
import { useResearchStream } from '../hooks/useResearchStream';

const ProgressPage: React.FC = () => {
  const { state, dispatch } = useResearch();
  const [isPolling, setIsPolling] = useState(false);
  const [currentProcess, setCurrentProcess] = useState('');
  const [logs, setLogs] = useState<string[]>([]);
  
  // 使用研究流Hook
  const { state: streamState, isLoading: streamLoading, error: streamError, isConnected } = useResearchStream(state.planId || null);

  // 监听实时流状态变化
  useEffect(() => {
    if (streamState) {
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

      // 更新日志
      if (streamState.messages && !logs.includes(streamState.messages)) {
        setLogs(prev => [...prev, `📊 ${streamState.messages}`]);
      }
      
      // 更新当前进程
      if (streamState.current_stage) {
        setCurrentProcess(`当前阶段: ${streamState.current_stage}`);
      }
      
      // 如果研究完成，停止轮询
      if (streamState.status === 'completed') {
        setIsPolling(false);
        setCurrentProcess('研究完成');
        setLogs(prev => [...prev, '✅ 研究完成！']);
      }
    }
  }, [streamState, dispatch]);

  // 监听流错误
  useEffect(() => {
    if (streamError) {
      console.error('研究流错误:', streamError);
      setLogs(prev => [...prev, `❌ 研究流错误: ${streamError}`]);
    }
  }, [streamError]);

  // 页面加载时自动开始监控
  useEffect(() => {
    if (state.planId && (state.status === 'research_completed' || state.status === 'plan_generated')) {
      setIsPolling(true);
      setLogs(['🚀 开始监控研究进度...']);
    }
  }, [state.planId, state.status]);

  // 控制按钮处理函数
  const handleStartMonitoring = () => {
    setIsPolling(true);
    setLogs(['🚀 开始监控研究进度...']);
  };

  const handlePauseMonitoring = () => {
    setIsPolling(false);
    setLogs(prev => [...prev, '⏸️ 暂停监控']);
  };

  const handleStopMonitoring = () => {
    setIsPolling(false);
    setLogs(prev => [...prev, '⏹️ 停止监控']);
  };

  const handleRefresh = () => {
    setLogs(prev => [...prev, '🔄 刷新状态...']);
  };

  if (!state.planId) {
    return (
      <div className="max-w-4xl mx-auto text-center">
        <div className="bg-white/80 backdrop-blur-sm rounded-xl p-8 card-shadow">
          <p className="text-gray-600">请先开始研究流程</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-6xl mx-auto">
        {/* 实时流状态栏 */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl shadow-lg p-4 mb-6"
        >
          <div className="flex items-center space-x-3">
            <Radio className={`h-5 w-5 ${isConnected ? 'text-green-500' : 'text-gray-400'}`} />
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <span className={`text-sm font-medium ${isConnected ? 'text-green-600' : 'text-gray-600'}`}>
                  LangGraph {isConnected ? '已连接' : '待连接'}
                </span>
                {streamLoading && (
                  <span className="text-xs text-blue-500">加载中...</span>
                )}
              </div>
              {streamState && (
                <div className="text-xs text-gray-500 mt-1">
                  当前阶段: {streamState.current_stage || '等待开始'} | 
                  计划ID: {state.planId || '未设置'}
                </div>
              )}
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="bg-white rounded-2xl shadow-xl p-8 mb-6"
        >
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-3xl font-bold text-gray-800">研究进度监控</h1>
            <div className="flex items-center space-x-4">
              <button
                onClick={handleStartMonitoring}
                disabled={isPolling}
                className="flex items-center space-x-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-green-300 disabled:cursor-not-allowed transition-colors"
              >
                <Play size={18} />
                <span>开始监控</span>
              </button>
              <button
                onClick={handlePauseMonitoring}
                disabled={!isPolling}
                className="flex items-center space-x-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:bg-yellow-300 disabled:cursor-not-allowed transition-colors"
              >
                <Pause size={18} />
                <span>暂停监控</span>
              </button>
              <button
                onClick={handleStopMonitoring}
                className="flex items-center space-x-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
              >
                <Square size={18} />
                <span>停止监控</span>
              </button>
              <button
                onClick={handleRefresh}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                <RefreshCw size={18} />
                <span>刷新</span>
              </button>
            </div>
          </div>

          {/* Current Process */}
          {currentProcess && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-primary-50 border border-primary-200 rounded-xl p-4 mb-6"
            >
              <div className="flex items-center space-x-3">
                <div className="loading-spinner text-primary-600"></div>
                <span className="text-primary-800 font-medium">{currentProcess}</span>
              </div>
            </motion.div>
          )}

          {/* Progress Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
              <div className="flex items-center space-x-3">
                <Clock className="h-8 w-8 text-blue-500" />
                <div>
                  <p className="text-sm text-blue-600">研究状态</p>
                  <p className="text-2xl font-bold text-blue-800">
                    {state.status === 'completed' ? '已完成' : 
                     state.status === 'research_completed' ? '研究中' : 
                     state.status === 'plan_generated' ? '计划生成' : 
                     state.status === 'awaiting_confirmation' ? '等待确认' : 
                     '待开始'}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-green-50 border border-green-200 rounded-xl p-4">
              <div className="flex items-center space-x-3">
                <CheckCircle className="h-8 w-8 text-green-500" />
                <div>
                  <p className="text-sm text-green-600">当前阶段</p>
                  <p className="text-2xl font-bold text-green-800">
                    {state.currentStage || '未开始'}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
              <div className="flex items-center space-x-3">
                <Play className="h-8 w-8 text-yellow-500" />
                <div>
                  <p className="text-sm text-yellow-600">步骤结果</p>
                  <p className="text-2xl font-bold text-yellow-800">
                    {state.stepResults?.length || 0}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
              <div className="flex items-center space-x-3">
                <AlertCircle className="h-8 w-8 text-gray-500" />
                <div>
                  <p className="text-sm text-gray-600">研究计划</p>
                  <p className="text-2xl font-bold text-gray-800">
                    {state.currentPlan ? '已生成' : '未生成'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Detailed Steps */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Steps */}
            <div>
              <h3 className="text-lg font-semibold text-gray-800 mb-4">研究步骤</h3>
              <div className="space-y-3">
                {state.currentPlan?.steps?.map((step: any, index: number) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={`p-4 rounded-xl border transition-all duration-300 ${
                      step.status === 'completed'
                        ? 'bg-green-50 border-green-200'
                        : step.status === 'in_progress'
                        ? 'bg-blue-50 border-blue-200'
                        : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                        step.status === 'completed'
                          ? 'bg-green-500 text-white'
                          : step.status === 'in_progress'
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-300 text-gray-600'
                      }`}>
                        {step.status === 'completed' ? (
                          <CheckCircle className="h-4 w-4" />
                        ) : (
                          index + 1
                        )}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-800">{step.title}</h4>
                        <p className="text-sm text-gray-600 mt-1">{step.description}</p>
                        {step.result && (
                          <p className="text-sm text-green-700 mt-2 p-2 bg-green-100 rounded-lg">
                            {step.result}
                          </p>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )) || (
                  <div className="text-center text-gray-500 p-8">
                    <p>暂无研究步骤信息</p>
                  </div>
                )}
              </div>
            </div>

            {/* Logs */}
            <div>
              <h3 className="text-lg font-semibold text-gray-800 mb-4">执行日志</h3>
              <div className="bg-gray-900 rounded-xl p-4 h-96 overflow-y-auto">
                <AnimatePresence>
                  {logs.map((log, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      className="text-sm text-gray-300 mb-2 font-mono"
                    >
                      <span className="text-gray-500">[{new Date().toLocaleTimeString()}]</span> {log}
                    </motion.div>
                  ))}
                </AnimatePresence>
                {(state.status === 'pending' || state.status === 'coordinate' || state.status === 'plan_generated' || state.status === 'awaiting_confirmation') && (
                  <div className="flex items-center space-x-2 text-blue-400">
                    <div className="loading-spinner h-3 w-3"></div>
                    <span className="text-sm">正在执行...</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default ProgressPage;