import { useEffect, useRef } from 'react';
import { useStreamingStore } from '../../store/streamingStore';
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { clsx } from 'clsx';

export function StreamingProgress() {
  const { logs, status, activeAgent, error } = useStreamingStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  if (status === 'idle') return null;

  return (
    <div className="card border-slate-800 bg-slate-900/80 shadow-2xl overflow-hidden flex flex-col flex-1 h-[400px]">
      <div className="p-4 border-b border-slate-800 bg-slate-900 flex justify-between items-center">
        <div className="flex items-center gap-3">
          {status === 'running' ? (
             <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-500/10 text-primary-500">
                <Loader2 className="w-4 h-4 animate-spin" />
             </div>
          ) : status === 'done' ? (
             <div className="flex items-center justify-center w-8 h-8 rounded-full bg-success-500/10 text-success-500">
                <CheckCircle2 className="w-4 h-4" />
             </div>
          ) : status === 'error' ? (
             <div className="flex items-center justify-center w-8 h-8 rounded-full bg-danger-500/10 text-danger-500">
                <AlertCircle className="w-4 h-4" />
             </div>
          ) : (
             <div className="flex items-center justify-center w-8 h-8 rounded-full bg-warning-500/10 text-warning-500 animate-pulse">
                <AlertCircle className="w-4 h-4" />
             </div>
          )}
          
          <div>
            <h3 className="font-semibold text-slate-100 flex items-center gap-2">
              Pipeline Status: <span className="capitalize">{status.replace('_', ' ')}</span>
            </h3>
            {activeAgent && (
              <p className="text-xs text-primary-400 font-mono mt-0.5">{activeAgent}</p>
            )}
          </div>
        </div>
      </div>
      
      <div className="p-4 overflow-y-auto flex-1 font-mono text-sm space-y-2">
        {logs.map((log, i) => (
          <div key={i} className="flex gap-3 text-slate-400 group">
             <span className="text-slate-600 shrink-0">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
             <span className={clsx(
               "flex-1",
               log.event_type === 'error' && "text-danger-400",
               log.event_type === 'agent_complete' && "text-success-400",
               log.event_type === 'agent_start' && "text-blue-400",
             )}>
               <span className="uppercase font-semibold opacity-70 mr-2">{log.agent_name}</span>
               {String(log.event_type) === 'message' ? String(log.data) : String(log.event_type)}
             </span>
          </div>
        ))}
        {error && (
          <div className="flex gap-3 text-danger-400 bg-danger-500/10 p-2 rounded">
             <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
             <span>{error}</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
