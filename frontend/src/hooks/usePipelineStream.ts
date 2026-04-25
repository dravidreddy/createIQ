import { useCallback, useRef } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useStreamingStore } from '../store/streamingStore';
import { useProjectStore } from '../store/projectStore';
import { StreamEvent } from '../types';
import { getBaseUrl } from '../services/api';

export const usePipelineStream = () => {
  const { 
    setStatus, setActiveAgent, addLog, setCost, setInterruptContext, setError, reset,
    appendStreamedContent, setMetrics, addMessage, updateLastAgentOutput
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

  // Node name → human-readable label
  const nodeLabels: Record<string, string> = {
    load_memory: '📂 Loading your preferences...',
    validate_inputs: '🛡️ Validating inputs...',
    trend_research: '🔍 Scanning trending topics...',
    idea_generation: '💡 Brainstorming content angles...',
    idea_ranking: '🏆 Ranking ideas by potential...',
    hook_creation: '🪝 Crafting attention hooks...',
    hook_evaluation: '📊 Evaluating hook quality...',
    deep_research: '📚 Deep diving into research...',
    script_drafting: '✍️ Writing the first draft...',
    fact_checking: '🔬 Verifying facts and sources...',
    structure_analysis: '🏗️ Analyzing script structure...',
    pacing_optimization: '⚡ Optimizing pacing...',
    line_editing: '✏️ Polishing language and tone...',
    engagement_boosting: '🚀 Adding engagement triggers...',
    final_review: '👀 Final quality review...',
    series_planning: '📅 Building content strategy...',
    growth_advisory: '📈 Generating growth tips...',
    save_results: '💾 Saving your content...',
    thumbnail_brief: '🎨 Creating thumbnail brief...',
    evaluate: '📊 Evaluating quality...',
    summarize_context: '📝 Summarizing context...',
    state_sentinel: '🛡️ Running safety checks...',
  };

  const releaseBuffer = useCallback(() => {
    if (eventBufferRef.current.size === 0) return;
    
    const sortedSeqs = Array.from(eventBufferRef.current.keys()).sort((a, b) => a - b);
    const nextAvailable = sortedSeqs[0];
    
    console.warn(`Gap release triggered: Skipping to seq ${nextAvailable}`);
    const nextEvent = eventBufferRef.current.get(nextAvailable);
    eventBufferRef.current.delete(nextAvailable);
    
    lastSeqRef.current = nextAvailable - 1;
    processEvent(nextEvent);
  }, []);

  // Batching logic to reduce re-render lag (Tier 4)
  const flushBatch = useCallback(() => {
    if (batchQueueRef.current.length === 0) return;
    
    const batch = [...batchQueueRef.current];
    batchQueueRef.current = [];
    
    const _id = () => `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

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
        
        // Agent Thinking / Activity → Chat messages
        else if (type === 'agent_start' || type === 'group_start') {
            setActiveAgent(event.content || event.node || event.stage);
            addLog(event);
            const node = event.node || event.stage || '';
            const label = nodeLabels[node] || event.content || `Running ${node}...`;
            addMessage({
                id: _id(), role: 'agent', type: 'thinking',
                content: typeof label === 'string' ? label : String(label),
                node, timestamp: Date.now(),
            });
        } 
        
        // Backend thinking events (Option A rich progress)
        else if (type === 'thinking' || type === 'progress') {
            const msg = typeof event.content === 'string' ? event.content : (event as any).message || (event as any).data?.message || '';
            if (msg) {
                addMessage({
                    id: _id(), role: 'agent', type: 'thinking',
                    content: msg, node: event.node, timestamp: Date.now(),
                });
            }
        }
        
        // Tokens → stream into last agent output bubble
        else if (type === 'token') {
            const token = typeof event.content === 'string' ? event.content : (event as any).data?.token;
            appendStreamedContent(token, event.node);
            updateLastAgentOutput(token);
        } 
        
        // Performance & Telemetry
        else if (type === 'metrics') {
            setMetrics(event);
        }
        else if (type === 'agent_complete' || type === 'node_complete') {
            const cost = event.cost_cents ?? (event as any).data?.total_cost;
            if (cost !== undefined) setCost(cost);
            addLog(event);
            // Progress checkmark in chat
            const node = event.node || '';
            if (node && !['evaluate', 'summarize_context', 'state_sentinel', 'auto_approve_ideas', 'auto_approve_hooks'].includes(node)) {
                addMessage({
                    id: _id(), role: 'agent', type: 'progress',
                    content: `✓ ${node.replace(/_/g, ' ')}`,
                    node, timestamp: Date.now(),
                });
            }
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
            addMessage({
                id: _id(), role: 'system', type: 'interrupt',
                content: interruptData?.message || 'Your input is needed',
                timestamp: Date.now(),
            });
        } 
        
        // Failure & Recovery
        else if (type === 'error') {
            setStatus('error');
            const errorMsg = typeof event.content === 'string' ? event.content : (event as any).data?.message;
            setError(errorMsg || 'Pipeline error');
            addMessage({
                id: _id(), role: 'system', type: 'error',
                content: errorMsg || 'Pipeline error',
                timestamp: Date.now(),
            });
        } 
        
        // Standardized Termination
        else if (type === 'stream_end') {
            const status = (event.status || 'done') as string;
            if (status === 'interrupted') setStatus('interrupted');
            else if (status === 'error') setStatus('error');
            else if (status === 'cancelled') setStatus('done');
            else setStatus('done');
            
            if (event.final) {
                if (gapTimerRef.current) clearTimeout(gapTimerRef.current);
            }
        }

        addStreamEvent(event);
    });

    rafRef.current = null;
  }, [addLog, addStreamEvent, setActiveAgent, setCost, setError, setInterruptContext, setStatus, appendStreamedContent, setMetrics, addMessage, updateLastAgentOutput]);

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

    const API_BASE = getBaseUrl().replace(/\/api\/v1$/, '');

    try {
      await fetchEventSource(`${API_BASE}/api/v1/pipeline/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'include',
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

    let retryCount = 0;
    const MAX_RETRIES = 3;

    const API_BASE = getBaseUrl().replace(/\/api\/v1$/, '');

    try {
      await fetchEventSource(`${API_BASE}/api/v1/pipeline/${threadId}/resume`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'include',
        body: JSON.stringify({ action, stage, ...contentData }),
        signal: ctrl.signal,
        async onopen(response) {
          if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
              setStatus('error');
              setError('Session expired. Please log in again.');
              throw new Error(`Auth failed: ${response.status}`);
            }
          }
        },
        onmessage(msg) {
          if (!msg.data) return;
          retryCount = 0; // Reset on successful message
          try {
            processEvent(JSON.parse(msg.data));
          } catch (e) {
            console.warn('SSE Parse Error', e);
          }
        },
        onclose() {
          const currentStatus = useStreamingStore.getState().status;
          if (currentStatus === 'running') setStatus('done');
        },
        onerror(err) {
          retryCount++;
          if (retryCount >= MAX_RETRIES) {
            setStatus('error');
            setError('Pipeline connection failed after multiple retries.');
            throw err; // Stop retrying
          }
          // Allow fetchEventSource to retry with backoff
          console.warn(`Resume stream error (attempt ${retryCount}/${MAX_RETRIES}):`, err);
        }
      });
    } catch (err) {
      console.error(err);
      const currentStatus = useStreamingStore.getState().status;
      if (currentStatus !== 'error') setStatus('error');
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
    const API_BASE = getBaseUrl().replace(/\/api\/v1$/, '');
    const url = lastSeq !== undefined 
        ? `${API_BASE}/api/v1/pipeline/${threadId}/status?last_seq=${lastSeq}`
        : `${API_BASE}/api/v1/pipeline/${threadId}/status`;

    try {
      const res = await fetch(url, {
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
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
