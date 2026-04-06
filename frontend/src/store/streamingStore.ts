import { create } from 'zustand';
import { StreamEvent } from '../types';

interface StreamState {
  status: 'idle' | 'running' | 'interrupted' | 'error' | 'done';
  activeAgent: string | null;
  logs: StreamEvent[];
  cost: number;
  interruptContext: { stage: string; message: string; data: any } | null;
  error: string | null;
  streamedContent: string; // Legacy/Current fallback
  nodeContent: Record<string, string>; // Node-isolated content
  metrics: { ttft?: number; latency?: number; tps?: number } | null;
  threadId: string | null;

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
  reset: () => void;
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
      streamedContent: state.streamedContent + token // Also append to legacy for safety
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
    }),
}));
