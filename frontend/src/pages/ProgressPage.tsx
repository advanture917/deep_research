import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useResearch } from '../context/ResearchContext';
import { Play, Pause, Square, CheckCircle, Clock, AlertCircle } from 'lucide-react';

const ProgressPage: React.FC = () => {
  const { state, dispatch } = useResearch();
  const [isRunning, setIsRunning] = useState(false);
  const [currentProcess, setCurrentProcess] = useState('');
  const [logs, setLogs] = useState<string[]>([]);

  // 轮询研究进度
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isRunning && state.currentPlan) {
      const pollProgress = async () => {
        try {
          const response = await fetch(`http://localhost:8000/api/research/progress/${state.currentPlan!.id}`);
          if (response.ok) {
            const progress = await response.json();
            setCurrentProcess(progress.current_process);
            setLogs(progress.logs);
            
            // 更新步骤状态
            if (state.currentPlan) {
              const updatedSteps = [...state.currentPlan.steps];
              // 这里可以根据进度更新步骤状态
              dispatch({ type: 'SET_PLAN', payload: { ...state.currentPlan, steps: updatedSteps } });
            }
            
            // 检查是否完成
            if (progress.status === 'completed') {
              setIsRunning(false);
              setCurrentProcess('研究完成');
            }
          }
        } catch (error) {
          console.error('获取进度失败:', error);
        }
      };
      
      // 立即获取一次进度
      pollProgress();
      // 然后每2秒轮询一次
      interval = setInterval(pollProgress, 2000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRunning, state.currentPlan, dispatch]);

  const handleStart = () => {
    setIsRunning(true);
    setLogs(['🚀 开始执行研究计划...']);
  };

  const handlePause = () => {
    setIsRunning(false);
    setLogs(prev => [...prev, '⏸️ 研究过程已暂停']);
  };

  const handleStop = async () => {
    setIsRunning(false);
    
    try {
      if (state.currentPlan) {
        const response = await fetch(`http://localhost:8000/api/research/stop/${state.currentPlan.id}`, {
          method: 'POST',
        });
        
        if (response.ok) {
          setCurrentProcess('');
          setLogs([]);
          // 重置所有步骤状态
          state.currentPlan.steps.forEach((_, index) => {
            dispatch({
              type: 'UPDATE_STEP_STATUS',
              payload: { stepIndex: index, status: 'pending' },
            });
          });
        }
      }
    } catch (error) {
      console.error('停止研究失败:', error);
    }
  };

  if (!state.currentPlan) {
    return (
      <div className="max-w-4xl mx-auto text-center">
        <div className="bg-white/80 backdrop-blur-sm rounded-xl p-8 card-shadow">
          <p className="text-gray-600">请先制定研究计划</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 card-shadow mb-6"
      >
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-bold text-gray-900">研究进度</h1>
          <div className="flex space-x-3">
            {!isRunning ? (
              <button
                onClick={handleStart}
                className="flex items-center space-x-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-all duration-200"
              >
                <Play className="h-4 w-4" />
                <span>开始研究</span>
              </button>
            ) : (
              <>
                <button
                  onClick={handlePause}
                  className="flex items-center space-x-2 px-4 py-2 bg-accent-500 hover:bg-accent-600 text-white rounded-lg transition-all duration-200"
                >
                  <Pause className="h-4 w-4" />
                  <span>暂停</span>
                </button>
                <button
                  onClick={handleStop}
                  className="flex items-center space-x-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-all duration-200"
                >
                  <Square className="h-4 w-4" />
                  <span>停止</span>
                </button>
              </>
            )}
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
                <p className="text-sm text-blue-600">总步骤</p>
                <p className="text-2xl font-bold text-blue-800">{state.currentPlan.steps.length}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-green-50 border border-green-200 rounded-xl p-4">
            <div className="flex items-center space-x-3">
              <CheckCircle className="h-8 w-8 text-green-500" />
              <div>
                <p className="text-sm text-green-600">已完成</p>
                <p className="text-2xl font-bold text-green-800">
                  {state.currentPlan.steps.filter(s => s.status === 'completed').length}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
            <div className="flex items-center space-x-3">
              <Play className="h-8 w-8 text-yellow-500" />
              <div>
                <p className="text-sm text-yellow-600">进行中</p>
                <p className="text-2xl font-bold text-yellow-800">
                  {state.currentPlan.steps.filter(s => s.status === 'in_progress').length}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
            <div className="flex items-center space-x-3">
              <AlertCircle className="h-8 w-8 text-gray-500" />
              <div>
                <p className="text-sm text-gray-600">待开始</p>
                <p className="text-2xl font-bold text-gray-800">
                  {state.currentPlan.steps.filter(s => s.status === 'pending').length}
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
              {state.currentPlan.steps.map((step, index) => (
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
              ))}
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
              {isRunning && (
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
  );
};

export default ProgressPage;