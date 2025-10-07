// 暂时不使用LangGraph SDK的客户端，直接使用fetch API
// 后续可以集成LangGraph SDK的实时流功能

// 研究状态类型

// 研究状态类型
export interface ResearchState {
  messages: string;
  need_plan: boolean;
  plan_id?: string;
  status: 'pending' | 'coordinate' | 'plan_generated' | 'awaiting_confirmation' | 'research_completed' | 'completed';
  current_stage?: string;
  current_plan?: any;
  research_summary?: string;
  step_results?: any[];
  error?: string;
}

// 开始研究流程
export const startResearch = async (topic: string, locale: string = 'zh-CN'): Promise<ResearchState> => {
  const response = await fetch('/api/research/start', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ topic, locale }),
  });

  if (!response.ok) {
    throw new Error(`开始研究失败: ${response.statusText}`);
  }

  return await response.json();
};

// 确认研究计划
export const confirmPlan = async (planId: string, userConfirm: 'confirm' | 'modify', message?: string): Promise<ResearchState> => {
  const response = await fetch('/api/research/confirm-plan', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      plan_id: planId,
      user_confirm: userConfirm,
      message,
    }),
  });

  if (!response.ok) {
    throw new Error(`确认计划失败: ${response.statusText}`);
  }

  return await response.json();
};

// 获取研究状态
export const getResearchStatus = async (planId: string): Promise<ResearchState> => {
  const response = await fetch(`/api/research/status/${planId}`);

  if (!response.ok) {
    throw new Error(`获取研究状态失败: ${response.statusText}`);
  }

  return await response.json();
};

// 创建实时流监听器
export const createResearchStream = (planId: string) => {
  // 这里可以集成LangGraph SDK的实时流功能
  // 目前先使用轮询方式，后续可以升级为WebSocket
  return {
    subscribe: (callback: (state: ResearchState) => void) => {
      const interval = setInterval(async () => {
        try {
          const status = await getResearchStatus(planId);
          callback(status);
          
          // 如果研究已完成或需要用户确认计划，停止轮询
          if (status.status === 'completed' || status.status === 'awaiting_confirmation' || status.status === 'plan_generated') {
            clearInterval(interval);
          }
        } catch (error) {
          console.error('获取研究状态失败:', error);
        }
      }, 2000); // 每2秒轮询一次

      return () => clearInterval(interval);
    },
  };
};