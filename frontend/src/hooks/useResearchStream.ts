import { useState, useEffect, useRef } from 'react';
import { ResearchState, createResearchStream } from '../services/researchService';

// 研究流状态
export interface ResearchStreamState {
  state: ResearchState | null;
  isLoading: boolean;
  error: string | null;
  isConnected: boolean;
}

// 自定义Hook：使用LangGraph实时流
export const useResearchStream = (planId: string | null) => {
  const [streamState, setStreamState] = useState<ResearchStreamState>({
    state: null,
    isLoading: false,
    error: null,
    isConnected: false,
  });

  const streamRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!planId) {
      return;
    }

    setStreamState(prev => ({ ...prev, isLoading: true, error: null }));

    // 创建研究流
    const stream = createResearchStream(planId);
    
    streamRef.current = stream.subscribe((state: ResearchState) => {
      setStreamState({
        state,
        isLoading: false,
        error: null,
        isConnected: true,
      });
      
      // 如果研究已完成或需要用户确认计划，停止轮询
      if (state.status === 'completed' || state.status === 'awaiting_confirmation' || state.status === 'plan_generated') {
        disconnect();
      }
    });

    // 清理函数
    return () => {
      if (streamRef.current) {
        streamRef.current();
        streamRef.current = null;
      }
    };
  }, [planId]);

  // 手动连接/断开连接
  const connect = () => {
    if (planId && !streamRef.current) {
      const stream = createResearchStream(planId);
    streamRef.current = stream.subscribe((state: ResearchState) => {
      setStreamState({
        state,
        isLoading: false,
        error: null,
        isConnected: true,
      });
      
      // 如果研究已完成或需要用户确认计划，停止轮询
      if (state.status === 'completed' || state.status === 'awaiting_confirmation' || state.status === 'plan_generated') {
        disconnect();
      }
    });
    }
  };

  const disconnect = () => {
    if (streamRef.current) {
      streamRef.current();
      streamRef.current = null;
      setStreamState(prev => ({ ...prev, isConnected: false }));
    }
  };

  return {
    ...streamState,
    connect,
    disconnect,
  };
};