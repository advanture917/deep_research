import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useResearch, ResearchPlan } from '../context/ResearchContext';
import { Check, Edit3, X, ArrowRight, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { confirmPlan } from '../services/researchService';

const PlanPage: React.FC = () => {
  const { state, dispatch } = useResearch();
  const [isEditing, setIsEditing] = useState(false);
  const [editedPlan, setEditedPlan] = useState<ResearchPlan | null>(state.currentPlan);
  const [isLoading, setIsLoading] = useState(false);
  const [modifyMessage, setModifyMessage] = useState('');
  const navigate = useNavigate();

  // 监听状态变化，当研究完成时导航到报告页面
  React.useEffect(() => {
    if (state.status === 'completed') {
      navigate('/report');
    }
  }, [state.status, navigate]);

  // 从后端状态中获取计划信息
  React.useEffect(() => {
    console.log('PlanPage - 当前状态:', {
      status: state.status,
      currentPlan: state.currentPlan,
      planId: state.planId,
      needPlan: state.needPlan
    });
    
    if (state.currentPlan && state.currentPlan.steps) {
      // 如果已经有计划，直接使用
      setEditedPlan(state.currentPlan);
    } else if (state.currentPlan) {
      // 从后端状态中创建计划
      const backendPlan = state.currentPlan;
      const plan: ResearchPlan = {
        id: state.planId || `plan-${Date.now()}`,
        title: `关于"${state.researchTopic}"的研究计划`,
        thought: backendPlan.thought || "基于当前主题，我制定了一个全面的研究计划。",
        steps: backendPlan.steps?.map((step: any, index: number) => ({
          title: step.title || `步骤 ${index + 1}`,
          description: step.description || "",
          status: 'pending' as const,
        })) || [],
      };
      dispatch({ type: 'SET_PLAN', payload: plan });
      setEditedPlan(plan);
    }
  }, [state.currentPlan, state.researchTopic, state.planId, dispatch]);

  const handleConfirmPlan = async () => {
    setIsLoading(true);
    
    try {
      if (!state.planId) {
        throw new Error('计划ID不存在');
      }

      // 使用研究服务确认计划
      const result = await confirmPlan(state.planId, 'confirm');
      
      // 更新状态
      dispatch({
        type: 'UPDATE_FROM_BACKEND',
        payload: {
          status: result.status,
          currentStage: result.current_stage,
          needPlan: result.need_plan,
          researchSummary: result.research_summary,
          stepResults: result.step_results || [],
          currentPlan: result.current_plan || state.currentPlan,
        },
      });

      // 添加确认消息
      dispatch({
        type: 'ADD_MESSAGE',
        payload: {
          id: Date.now().toString(),
          role: 'assistant',
          content: '研究计划已确认，开始执行研究流程...',
          timestamp: new Date(),
        },
      });

      // 导航到进度页面
      navigate('/progress');
    } catch (error) {
      console.error('确认计划失败:', error);
      alert('确认计划失败，请稍后重试');
    } finally {
      setIsLoading(false);
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

  const handleModifyPlan = async () => {
    if (!state.planId || !modifyMessage.trim()) {
      alert('请输入修改意见');
      return;
    }

    setIsLoading(true);
    
    try {
      // 使用研究服务修改计划
      const result = await confirmPlan(state.planId, 'modify', modifyMessage);
      
      // 更新状态
      dispatch({
        type: 'UPDATE_FROM_BACKEND',
        payload: {
          status: result.status,
          currentStage: result.current_stage,
          needPlan: result.need_plan,
          currentPlan: result.current_plan,
          researchSummary: result.research_summary,
          stepResults: result.step_results || [],
        },
      });

      // 添加修改消息
      dispatch({
        type: 'ADD_MESSAGE',
        payload: {
          id: Date.now().toString(),
          role: 'assistant',
          content: '已收到您的修改意见，正在重新生成研究计划...',
          timestamp: new Date(),
        },
      });

      // 重置修改消息
      setModifyMessage('');
      setIsEditing(false);
    } catch (error) {
      console.error('修改计划失败:', error);
      alert('修改计划失败，请稍后重试');
    } finally {
      setIsLoading(false);
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

        {/* 修改计划界面 */}
        {isEditing && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg"
          >
            <h4 className="text-lg font-semibold text-yellow-800 mb-3">修改研究计划</h4>
            <textarea
              value={modifyMessage}
              onChange={(e) => setModifyMessage(e.target.value)}
              placeholder="请描述您希望如何修改研究计划..."
              className="w-full p-3 border border-yellow-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent resize-none min-h-[100px]"
            />
            <div className="flex justify-end space-x-3 mt-3">
              <button
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleModifyPlan}
                disabled={!modifyMessage.trim() || isLoading}
                className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? '提交中...' : '提交修改'}
              </button>
            </div>
          </motion.div>
        )}

        <div className="mt-8 flex justify-end space-x-3">
          <button
            onClick={() => navigate('/')}
            className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl font-semibold hover:bg-gray-300 transition-colors"
          >
            返回聊天
          </button>
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