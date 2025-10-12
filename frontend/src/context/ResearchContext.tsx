import React, { createContext, useContext, useReducer, ReactNode } from 'react';

// 研究状态类型定义
export interface ResearchState {
  researchTopic: string;
  locale: string;
  currentPlan: ResearchPlan | null;
  messages: Message[];
  isLoading: boolean;
  currentStep: number;
  researchResults: ResearchResult[];
  researchLoopCount: number;
  maxResearchLoops: number;
  planId: string | null;
  status: 'pending' | 'coordinate' | 'plan_generated' | 'awaiting_confirmation' | 'research_completed' | 'completed';
  currentStage: string | null;
  researchSummary: string | null;
  stepResults: any[];
  needPlan: boolean;
  message?: string; // 后端返回的消息字段
  error?: string; // 后端返回的错误字段
}

export interface ResearchPlan {
  id: string;
  title: string;
  thought: string;
  steps: ResearchStep[];
}

export interface ResearchStep {
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  result?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface ResearchResult {
  step: number;
  title: string;
  content: string;
  sources: Source[];
}

export interface Source {
  title: string;
  url: string;
  snippet: string;
}

// 初始状态
const initialState: ResearchState = {
  researchTopic: '',
  locale: 'zh-CN',
  currentPlan: null,
  messages: [],
  isLoading: false,
  currentStep: 0,
  researchResults: [],
  researchLoopCount: 0,
  maxResearchLoops: 3,
  planId: null,
  status: 'pending',
  currentStage: null,
  researchSummary: null,
  stepResults: [],
  needPlan: false,
};

// Action类型
type ResearchAction =
  | { type: 'SET_TOPIC'; payload: string }
  | { type: 'SET_LOCALE'; payload: string }
  | { type: 'SET_PLAN'; payload: ResearchPlan }
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'UPDATE_MESSAGE_CONTENT'; payload: { id: string; content: string } }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_CURRENT_STEP'; payload: number }
  | { type: 'UPDATE_STEP_STATUS'; payload: { stepIndex: number; status: ResearchStep['status']; result?: string } }
  | { type: 'ADD_RESEARCH_RESULT'; payload: ResearchResult }
  | { type: 'SET_RESEARCH_LOOP_COUNT'; payload: number }
  | { type: 'RESET_RESEARCH' }
  | { type: 'SET_PLAN_ID'; payload: string }
  | { type: 'SET_STATUS'; payload: ResearchState['status'] }
  | { type: 'SET_CURRENT_STAGE'; payload: string | null }
  | { type: 'SET_RESEARCH_SUMMARY'; payload: string | null }
  | { type: 'SET_STEP_RESULTS'; payload: any[] }
  | { type: 'SET_NEED_PLAN'; payload: boolean }
  | { type: 'UPDATE_FROM_BACKEND'; payload: Partial<ResearchState> };

// Reducer函数
const researchReducer = (state: ResearchState, action: ResearchAction): ResearchState => {
  switch (action.type) {
    case 'SET_TOPIC':
      return { ...state, researchTopic: action.payload };
    case 'SET_LOCALE':
      return { ...state, locale: action.payload };
    case 'SET_PLAN':
      return { ...state, currentPlan: action.payload };
    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'UPDATE_MESSAGE_CONTENT':
      return {
        ...state,
        messages: state.messages.map(m => m.id === action.payload.id ? { ...m, content: action.payload.content } : m),
      };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_CURRENT_STEP':
      return { ...state, currentStep: action.payload };
    case 'UPDATE_STEP_STATUS':
      if (!state.currentPlan) return state;
      const updatedSteps = [...state.currentPlan.steps];
      updatedSteps[action.payload.stepIndex] = {
        ...updatedSteps[action.payload.stepIndex],
        status: action.payload.status,
        result: action.payload.result,
      };
      return {
        ...state,
        currentPlan: {
          ...state.currentPlan,
          steps: updatedSteps,
        },
      };
    case 'ADD_RESEARCH_RESULT':
      return {
        ...state,
        researchResults: [...state.researchResults, action.payload],
      };
    case 'SET_RESEARCH_LOOP_COUNT':
      return { ...state, researchLoopCount: action.payload };
    case 'SET_PLAN_ID':
      return { ...state, planId: action.payload };
    case 'SET_STATUS':
      return { ...state, status: action.payload };
    case 'SET_CURRENT_STAGE':
      return { ...state, currentStage: action.payload };
    case 'SET_RESEARCH_SUMMARY':
      return { ...state, researchSummary: action.payload };
    case 'SET_STEP_RESULTS':
      return { ...state, stepResults: action.payload };
    case 'SET_NEED_PLAN':
      return { ...state, needPlan: action.payload };
    case 'UPDATE_FROM_BACKEND':
      return { ...state, ...action.payload };
    case 'RESET_RESEARCH':
      return initialState;
    default:
      return state;
  }
};

// Context
const ResearchContext = createContext<{
  state: ResearchState;
  dispatch: React.Dispatch<ResearchAction>;
}>({
  state: initialState,
  dispatch: () => null,
});

// Provider组件
export const ResearchProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(researchReducer, initialState);

  return (
    <ResearchContext.Provider value={{ state, dispatch }}>
      {children}
    </ResearchContext.Provider>
  );
};

// Hook
export const useResearch = () => {
  const context = useContext(ResearchContext);
  if (!context) {
    throw new Error('useResearch must be used within a ResearchProvider');
  }
  return context;
};