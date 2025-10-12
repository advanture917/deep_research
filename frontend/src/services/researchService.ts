// 暂时不使用LangGraph SDK的客户端，直接使用fetch API
// 增加基于 fetch+ReadableStream 的 SSE(POST) 支持

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

// ===== SSE 通用工具 =====
type ResearchSSEEvent =
  | 'started'
  | 'coordinate'
  | 'plan'
  | 'interrupt'
  | 'research'
  | 'done'
  | 'error'
  | 'chunk'
  | 'message';

export interface ResearchSSEHandlers {
  onStarted?: (data: any) => void;
  onCoordinate?: (data: any) => void;
  onPlan?: (data: any) => void;
  onInterrupt?: (data: any) => void;
  onResearch?: (data: any) => void;
  onDone?: (data: any) => void;
  onError?: (data: any) => void;
  onChunk?: (data: { plan_id?: string; delta?: string } | any) => void;
  onAny?: (event: ResearchSSEEvent, data: any) => void;
}

const parseSSE = (chunk: string, buffer: { pending: string }, dispatch: (event: ResearchSSEEvent, data: any) => void) => {
  buffer.pending += chunk;
  const events = buffer.pending.split('\n\n');
  // 保留最后一个未完成块
  buffer.pending = events.pop() || '';
  for (const rawEvent of events) {
    const lines = rawEvent.split('\n');
    let event: ResearchSSEEvent = 'message';
    const dataLines: string[] = [];
    for (const line of lines) {
      if (line.startsWith('event:')) {
        event = line.slice('event:'.length).trim() as ResearchSSEEvent;
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice('data:'.length).trim());
      }
    }
    const dataStr = dataLines.join('\n');
    let data: any = dataStr;
    try {
      data = JSON.parse(dataStr);
    } catch {
      // 非 JSON 数据，原样传递
    }
    dispatch(event, data);
  }
};

const ssePost = (url: string, body: any, handlers: ResearchSSEHandlers) => {
  const controller = new AbortController();
  const signal = controller.signal;
  const buffer = { pending: '' };
  const decoder = new TextDecoder();

  const dispatch = (event: ResearchSSEEvent, data: any) => {
    handlers.onAny && handlers.onAny(event, data);
    switch (event) {
      case 'started':
        handlers.onStarted && handlers.onStarted(data);
        break;
      case 'chunk':
        handlers.onChunk && handlers.onChunk(data);
        break;
      case 'coordinate':
        handlers.onCoordinate && handlers.onCoordinate(data);
        break;
      case 'plan':
        handlers.onPlan && handlers.onPlan(data);
        break;
      case 'interrupt':
        handlers.onInterrupt && handlers.onInterrupt(data);
        break;
      case 'research':
        handlers.onResearch && handlers.onResearch(data);
        break;
      case 'done':
        handlers.onDone && handlers.onDone(data);
        break;
      case 'error':
        handlers.onError && handlers.onError(data);
        break;
      default:
        break;
    }
  };

  (async () => {
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(body || {}),
        signal,
      });
      if (!resp.ok || !resp.body) {
        const msg = `SSE 请求失败: ${resp.status} ${resp.statusText}`;
        dispatch('error', { error: msg });
        dispatch('done', {});
        return;
      }
      const reader = resp.body.getReader();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        parseSSE(text, buffer, dispatch);
      }
      // flush 剩余
      if (buffer.pending) {
        parseSSE('\n\n', buffer, dispatch);
      }
      dispatch('done', {});
    } catch (e: any) {
      dispatch('error', { error: e?.message || String(e) });
      dispatch('done', {});
    }
  })();

  return { close: () => controller.abort() };
};

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

// ===== 基于 SSE 的启动研究流 =====
export const startResearchSSE = (
  topic: string,
  locale: string,
  handlers: ResearchSSEHandlers
) => {
  // 直连后端以避免开发代理对 SSE(POST) 的缓冲
  return ssePost('http://localhost:8000/api/research/start/stream?mode=messages', { topic, locale }, handlers);
};

// ===== 基于 SSE 的确认计划流 =====
export const confirmPlanSSE = (
  planId: string,
  userConfirm: 'confirm' | 'modify',
  message: string | undefined,
  handlers: ResearchSSEHandlers
) => {
  return ssePost('/api/research/confirm-plan/stream', { plan_id: planId, user_confirm: userConfirm, message }, handlers);
};