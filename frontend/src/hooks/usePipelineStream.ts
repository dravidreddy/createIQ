import { useCallback, useRef } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useStreamingStore } from '../store/streamingStore';
import { useProjectStore } from '../store/projectStore';
import { StreamEvent } from '../types';

export const usePipelineStream = () => {
  const { 
    setStatus, setActiveAgent, addLog, setCost, setInterruptContext, setError, reset,
    appendStreamedContent, setMetrics
  } = useStreamingStore();
  const { addStreamEvent } = useProjectStore();
  
  const ctrlRef = useRef<AbortController | null>(null);
  const lastSeqRef = useRef<number>(-1);
  const eventBufferRef = useRef<Map<number, any>>(new Map());
  const rafRef = useRef<number | null>(null);
  const batchQueueRef = useRef<any[]>([]);
  
  // Resilience Refs
  const gapTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastHeartbeatRef = useRef<number>(Date.now());

  const releaseBuffer = useCallback(() => {
    if (eventBufferRef.current.size === 0) return;
    
    // Sort keys and take the smallest available (the gap we were waiting for)
    const sortedSeqs = Array.from(eventBufferRef.current.keys()).sort((a, b) => a - b);
    const nextAvailable = sortedSeqs[0];
    
    console.warn(`Gap release triggered: Skipping to seq ${nextAvailable}`);
    const nextEvent = eventBufferRef.current.get(nextAvailable);
    eventBufferRef.current.delete(nextAvailable);
    
    // Jump forward
    lastSeqRef.current = nextAvailable - 1;
    processEvent(nextEvent);
  }, []);

  // Batching logic to reduce re-render lag (Tier 4)
  const flushBatch = useCallback(() => {
    if (batchQueueRef.current.length === 0) return;
    
    const batch = [...batchQueueRef.current];
    batchQueueRef.current = [];
    
    batch.forEach((event: StreamEvent) => {
        const type = event.type;
        
        // Lifecycle events
        if (type === 'stream_start') {
            lastHeartbeatRef.current = Date.now();
        } 
        else if (type === 'thread_created') {
            const threadId = event.content?.thread_id || (event as any).data?.thread_id;
            useStreamingStore.getState().setThreadId(threadId);
        } 
        
        // Transitions
        else if (type === 'agent_start' || type === 'group_start') {
            setActiveAgent(event.content || event.node || event.stage);
            addLog(event);
        } 
        
        // Tokens with Node Isolation
        else if (type === 'token') {
            const token = typeof event.content === 'string' ? event.content : (event as any).data?.token;
            appendStreamedContent(token, event.node);
        } 
        
        // Performance & Telemetry
        else if (type === 'metrics') {
            setMetrics(event);
        }
        else if (type === 'agent_complete' || type === 'node_complete') {
            const cost = event.cost_cents ?? (event as any).data?.total_cost;
            if (cost !== undefined) setCost(cost);
            addLog(event);
        } 
        
        // HITL Interrupts
        else if (type === 'interrupt') {
            setStatus('interrupted');
            setActiveAgent(null);
            const interruptData = event.content || (event as any).data;
            setInterruptContext({
                stage: event.stage || interruptData?.stage,
                message: interruptData?.message,
                data: interruptData?.output || interruptData?.data
            });
        } 
        
        // Failure & Recovery
        else if (type === 'error') {
            setStatus('error');
            const errorMsg = typeof event.content === 'string' ? event.content : (event as any).data?.message;
            setError(errorMsg || 'Pipeline error');
        } 
        
        // Standardized Termination
        else if (type === 'stream_end') {
            const status = event.status || 'done';
            if (status === 'interrupted') setStatus('interrupted');
            else if (status === 'error') setStatus('error');
            else setStatus('done');
            
            if (event.final) {
                // Clear any remaining gap timers
                if (gapTimerRef.current) clearTimeout(gapTimerRef.current);
            }
        }

        addStreamEvent(event);
    });

    rafRef.current = null;
  }, [addLog, addStreamEvent, setActiveAgent, setCost, setError, setInterruptContext, setStatus, appendStreamedContent, setMetrics]);

  const processEvent = useCallback((dataObj: any) => {
    const seq = dataObj.seq ?? dataObj.sequence_id ?? -1;
    
    // Heartbeat Tracking
    if (dataObj.type === 'heartbeat') {
        lastHeartbeatRef.current = Date.now();
    }

    // 1. Ordered delivery logic
    if (seq !== -1 && seq <= lastSeqRef.current) return;
    
    // Gap Detection
    if (seq !== -1 && seq > lastSeqRef.current + 1 && lastSeqRef.current !== -1) {
        if (eventBufferRef.current.size < 100) {
            eventBufferRef.current.set(seq, dataObj);
            
            // Set/Reset Gap Release Timer (300ms default)
            if (!gapTimerRef.current) {
                gapTimerRef.current = setTimeout(releaseBuffer, 300);
            }
        }
        return;
    }

    // Clear gap timer if we received the expected sequence
    if (gapTimerRef.current) {
        clearTimeout(gapTimerRef.current);
        gapTimerRef.current = null;
    }

    // 2. Queue for batching
    batchQueueRef.current.push(dataObj);
    if (!rafRef.current) {
        rafRef.current = requestAnimationFrame(flushBatch);
    }

    if (seq !== -1) lastSeqRef.current = seq;

    // 3. Recursive buffer drain
    const nextSeq = lastSeqRef.current + 1;
    if (eventBufferRef.current.has(nextSeq)) {
        const nextEvent = eventBufferRef.current.get(nextSeq);
        eventBufferRef.current.delete(nextSeq);
        processEvent(nextEvent);
    }
  }, [flushBatch, releaseBuffer]);

  const startPipeline = useCallback(async (
    projectId: string,
    topic: string,
    options: any = {}
  ) => {
    reset();
    lastSeqRef.current = -1;
    eventBufferRef.current.clear();
    batchQueueRef.current = [];
    setStatus('running');
    
    if (ctrlRef.current) ctrlRef.current.abort();
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;

    const token = localStorage.getItem('token');
    const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000';

    try {
      await fetchEventSource(`${API_BASE}/api/v1/pipeline/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ project_id: projectId, topic, ...options }),
        signal: ctrl.signal,
        async onopen(response) {
          if (!response.ok) {
            setStatus('error');
            setError(`Connection failed: ${response.status}`);
            throw new Error(`Error: ${response.status}`);
          }
        },
        onmessage(msg) {
          if (!msg.data) return;
          try {
            processEvent(JSON.parse(msg.data));
          } catch (e) {
            console.warn('SSE Parse Error', e);
          }
        },
        onclose() {
          const currentStatus = useStreamingStore.getState().status;
          if (currentStatus === 'running' || currentStatus === 'idle') {
             // Unexpected close -> Reconnect strategy (check status first)
             const threadId = useStreamingStore.getState().threadId;
             if (threadId) checkPipelineStatus(threadId, lastSeqRef.current);
          }
        },
        onerror(err) {
          setStatus('error');
          setError(err.message || 'Stream connection failed');
          throw err;
        }
      });
    } catch (err) {
      console.error("fetchEventSource throw:", err);
      setStatus('error');
    }
  }, [reset, setStatus, setError, processEvent]);

  const resumePipeline = useCallback(async (
    threadId: string,
    action: string,
    stage: string,
    contentData?: any
  ) => {
    setStatus('running');
    setInterruptContext(null);
    setActiveAgent('Resuming pipeline...');

    if (ctrlRef.current) ctrlRef.current.abort();
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;

    const token = localStorage.getItem('token');
    const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000';

    try {
      await fetchEventSource(`${API_BASE}/api/v1/pipeline/${threadId}/resume`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ action, stage, ...contentData }),
        signal: ctrl.signal,
        onmessage(msg) {
          if (!msg.data) return;
          try {
            processEvent(JSON.parse(msg.data));
          } catch (e) {
            console.warn('SSE Parse Error', e);
          }
        },
        onclose() {
          const currentStatus = useStreamingStore.getState().status;
          if (currentStatus === 'running') setStatus('done');
        }
      });
    } catch (err) {
      console.error(err);
      setStatus('error');
    }
  }, [setStatus, setInterruptContext, setActiveAgent, setError, processEvent]);

  const stopStream = useCallback(() => {
    if (ctrlRef.current) {
      ctrlRef.current.abort();
      ctrlRef.current = null;
    }
    if (gapTimerRef.current) clearTimeout(gapTimerRef.current);
  }, []);

  const checkPipelineStatus = useCallback(async (threadId: string, lastSeq?: number) => {
    const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000';
    const token = localStorage.getItem('token');
    const url = lastSeq !== undefined 
        ? `${API_BASE}/api/v1/pipeline/${threadId}/status?last_seq=${lastSeq}`
        : `${API_BASE}/api/v1/pipeline/${threadId}/status`;

    try {
      const res = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.total_cost_cents !== undefined) setCost(data.total_cost_cents);
        
        if (data.interrupt_data) {
           setStatus('interrupted');
           setActiveAgent(null);
           setInterruptContext({
               stage: data.interrupt_data.type || data.current_stage,
               message: data.interrupt_data.message,
               data: data.interrupt_data.current_output
           });
        } else if (data.current_stage) {
           setActiveAgent(`Running: ${data.current_stage}`);
           if (data.next_nodes && data.next_nodes.length === 0) setStatus('done');
        }
      }
    } catch (e) {
      console.error(e);
    }
  }, [setCost, setStatus, setActiveAgent, setInterruptContext]);

  return { startPipeline, resumePipeline, stopStream, checkPipelineStatus };
};
