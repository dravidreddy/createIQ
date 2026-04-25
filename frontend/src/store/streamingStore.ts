import { create } from 'zustand';
import { StreamEvent } from '../types';

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent' | 'system';
  type: 'prompt' | 'thinking' | 'output' | 'progress' | 'error' | 'interrupt';
  content: string;
  node?: string;
  timestamp: number;
}

interface StreamState {
  status: 'idle' | 'running' | 'interrupted' | 'error' | 'done';
  activeAgent: string | null;
  logs: StreamEvent[];
  cost: number;
  interruptContext: { stage: string; message: string; data: any } | null;
  error: string | null;
  streamedContent: string;
  nodeContent: Record<string, string>;
  metrics: { ttft?: number; latency?: number; tps?: number } | null;
  threadId: string | null;
  messages: ChatMessage[];

  // Actions
  setStatus: (status: StreamState['status']) => void;
  setActiveAgent: (agent: string | null) => void;
  addLog: (log: StreamEvent) => void;
  setCost: (cost: number) => void;
  setInterruptContext: (context: any) => void;
  setError: (error: string | null) => void;
  appendStreamedContent: (token: string, node?: string) => void;
  clearStreamedContent: (node?: string) => void;
  setMetrics: (metrics: any) => void;
  setThreadId: (id: string | null) => void;
  addMessage: (msg: ChatMessage) => void;
  updateLastAgentOutput: (token: string) => void;
  reset: () => void;
}

let _msgIdCounter = 0;
export function createMsgId(): string {
  return `msg_${Date.now()}_${++_msgIdCounter}`;
}

export const useStreamingStore = create<StreamState>((set) => ({
  status: 'idle',
  activeAgent: null,
  logs: [],
  cost: 0,
  interruptContext: null,
  error: null,
  streamedContent: '',
  nodeContent: {},
  metrics: null,
  threadId: null,
  messages: [],

  setStatus: (status) => set({ status }),
  setActiveAgent: (activeAgent) => set({ activeAgent }),
  addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
  setCost: (cost) => set({ cost }),
  setInterruptContext: (interruptContext) => set({ interruptContext }),
  setError: (error) => set({ error }),
  
  appendStreamedContent: (token, node) => set((state) => {
    if (!node) return { streamedContent: state.streamedContent + token };
    const prev = state.nodeContent[node] || '';
    return {
      nodeContent: { ...state.nodeContent, [node]: prev + token },
      streamedContent: state.streamedContent + token,
    };
  }),

  clearStreamedContent: (node) => set((state) => {
    if (!node) return { streamedContent: '' };
    const newContent = { ...state.nodeContent };
    delete newContent[node];
    return { nodeContent: newContent };
  }),

  setMetrics: (metrics) => set({ metrics }),
  setThreadId: (threadId) => set({ threadId }),

  addMessage: (msg) => set((state) => ({
    messages: [...state.messages, msg],
  })),

  updateLastAgentOutput: (token) => set((state) => {
    const msgs = [...state.messages];
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'agent' && msgs[i].type === 'output') {
        msgs[i] = { ...msgs[i], content: msgs[i].content + token };
        return { messages: msgs };
      }
    }
    msgs.push({
      id: `msg_${Date.now()}_${++_msgIdCounter}`,
      role: 'agent',
      type: 'output',
      content: token,
      timestamp: Date.now(),
    });
    return { messages: msgs };
  }),
  
  reset: () =>
    set({
      status: 'idle',
      activeAgent: null,
      logs: [],
      cost: 0,
      interruptContext: null,
      error: null,
      streamedContent: '',
      nodeContent: {},
      metrics: null,
      threadId: null,
      messages: [],
    }),
}));
