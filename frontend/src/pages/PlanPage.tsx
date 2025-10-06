import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useResearch, ResearchPlan } from '../context/ResearchContext';
import { Check, Edit3, X, ArrowRight, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const PlanPage: React.FC = () => {
  const { state, dispatch } = useResearch();
  const [isEditing, setIsEditing] = useState(false);
  const [editedPlan, setEditedPlan] = useState<ResearchPlan | null>(state.currentPlan);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  // 模拟生成研究计划
  React.useEffect(() => {
    if (!state.currentPlan && state.researchTopic) {
      const mockPlan = {
        id: `mock-${Date.now()}`,
        title: `关于"${state.researchTopic}"的深度研究计划`,
        thought: "基于当前主题，我制定了一个全面的研究计划，将从多个角度进行深入分析。",
        steps: [
          {
            title: "背景调研",
            description: "搜集相关背景信息，了解当前领域的最新发展状况",
            status: 'pending' as const,
          },
          {
            title: "关键问题分析",
            description: "识别和分析核心问题，确定研究的重点方向",
            status: 'pending' as const,
          },
          {
            title: "数据收集与验证",
            description: "收集相关数据和信息，进行事实核查和验证",
            status: 'pending' as const,
          },
          {
            title: "深度分析与综合",
            description: "对收集的信息进行深度分析，形成综合性结论",
            status: 'pending' as const,
          },
          {
            title: "报告生成",
            description: "基于研究结果生成专业的研究报告",
            status: 'pending' as const,
          },
        ],
      };
      dispatch({ type: 'SET_PLAN', payload: mockPlan });
      setEditedPlan(mockPlan);
    }
  }, [state.researchTopic, state.currentPlan, dispatch]);

  const handleConfirmPlan = async () => {
    setIsLoading(true);
    
    try {
      // 更新计划到后端
      if (editedPlan && state.currentPlan) {
        const response = await fetch(`http://localhost:8000/api/research/update-plan/${state.currentPlan.id}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(editedPlan),
        });

        if (response.ok) {
          const updatedPlan = await response.json();
          dispatch({ type: 'SET_PLAN', payload: updatedPlan });
          
          // 开始研究
          const startResponse = await fetch(`http://localhost:8000/api/research/start/${state.currentPlan.id}`, {
            method: 'POST',
          });

          if (startResponse.ok) {
            setIsLoading(false);
            navigate('/progress');
          } else {
            throw new Error('开始研究失败');
          }
        } else {
          throw new Error('更新计划失败');
        }
      }
    } catch (error) {
      console.error('确认计划失败:', error);
      setIsLoading(false);
      alert('确认计划失败，请稍后重试');
    }
  };

  const handleEditStep = (index: number, newDescription: string) => {
    if (!editedPlan) return;
    
    const updatedSteps = [...editedPlan.steps];
    updatedSteps[index] = {
      ...updatedSteps[index],
      description: newDescription,
    };
    
    setEditedPlan({
      ...editedPlan,
      steps: updatedSteps,
    });
  };

  const handleRegeneratePlan = () => {
    // 模拟重新生成计划
    if (state.researchTopic) {
      const newMockPlan = {
        id: `mock-${Date.now()}`,
        title: `关于"${state.researchTopic}"的优化研究计划`,
        thought: "基于反馈重新制定的研究计划，更加聚焦核心问题。",
        steps: [
          {
            title: "问题定义与范围界定",
            description: "明确研究问题的边界和核心要素",
            status: 'pending' as const,
          },
          {
            title: "文献综述",
            description: "系统梳理相关研究和理论基础",
            status: 'pending' as const,
          },
          {
            title: "实证研究",
            description: "基于实际数据和案例进行深入研究",
            status: 'pending' as const,
          },
          {
            title: "结果分析与讨论",
            description: "分析研究结果，探讨其意义和影响",
            status: 'pending' as const,
          },
          {
            title: "结论与建议",
            description: "形成研究结论，提出相关建议",
            status: 'pending' as const,
          },
        ],
      };
      dispatch({ type: 'SET_PLAN', payload: newMockPlan });
      setEditedPlan(newMockPlan);
    }
  };

  if (!state.currentPlan) {
    return (
      <div className="max-w-4xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-white/80 backdrop-blur-sm rounded-xl p-8 card-shadow"
        >
          <div className="loading-spinner mx-auto mb-4"></div>
          <p className="text-gray-600">正在生成研究计划...</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 card-shadow mb-6"
      >
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-bold text-gray-900">研究计划</h1>
          <div className="flex space-x-3">
            <button
              onClick={handleRegeneratePlan}
              className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-all duration-200 text-gray-700"
            >
              <RefreshCw className="h-4 w-4" />
              <span>重新生成</span>
            </button>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 ${
                isEditing
                  ? 'bg-accent-500 text-white hover:bg-accent-600'
                  : 'bg-primary-100 text-primary-700 hover:bg-primary-200'
              }`}
            >
              {isEditing ? <X className="h-4 w-4" /> : <Edit3 className="h-4 w-4" />}
              <span>{isEditing ? '取消编辑' : '编辑计划'}</span>
            </button>
          </div>
        </div>

        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">{state.currentPlan.title}</h2>
          <p className="text-gray-600 leading-relaxed">{state.currentPlan.thought}</p>
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">研究步骤</h3>
          {state.currentPlan.steps.map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="research-step"
            >
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center text-primary-700 font-semibold text-sm">
                  {index + 1}
                </div>
                <div className="flex-1">
                  <h4 className="text-lg font-semibold text-gray-800 mb-2">{step.title}</h4>
                  {isEditing ? (
                    <textarea
                      value={editedPlan?.steps[index].description || ''}
                      onChange={(e) => handleEditStep(index, e.target.value)}
                      className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                      rows={2}
                    />
                  ) : (
                    <p className="text-gray-600 leading-relaxed">{step.description}</p>
                  )}
                </div>
                <div className="flex-shrink-0">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                    step.status === 'completed' ? 'bg-green-100 text-green-600' :
                    step.status === 'in_progress' ? 'bg-blue-100 text-blue-600' :
                    step.status === 'failed' ? 'bg-red-100 text-red-600' :
                    'bg-gray-100 text-gray-400'
                  }`}>
                    {step.status === 'completed' && <Check className="h-4 w-4" />}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="mt-8 flex justify-end">
          <button
            onClick={handleConfirmPlan}
            disabled={isLoading}
            className={`flex items-center space-x-2 px-6 py-3 rounded-xl font-semibold transition-all duration-200 ${
              isLoading
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'btn-primary'
            }`}
          >
            {isLoading ? (
              <>
                <div className="loading-spinner"></div>
                <span>确认中...</span>
              </>
            ) : (
              <>
                <span>确认计划</span>
                <ArrowRight className="h-5 w-5" />
              </>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

export default PlanPage;