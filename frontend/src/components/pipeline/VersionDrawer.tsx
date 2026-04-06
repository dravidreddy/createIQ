import { History, X, Clock, CheckCircle2 } from 'lucide-react';
import { clsx } from 'clsx';

export function VersionDrawer({ isOpen, onClose, projectId }: { isOpen: boolean, onClose: () => void, projectId: string }) {
  // Static mock since backend VersionService is not fully wired to a stream fetch just yet
  // Once the v4 endpoint exposes GET /pipeline/{id}/versions, this will be hydrated
  const versions = [
    { id: '1', date: new Date().toISOString(), title: 'Initial Draft', is_current: false, changes: 'Idea generation and script drafting.' },
    { id: '2', date: new Date().toISOString(), title: 'Edited Polish', is_current: true, changes: 'Applied screenplay guidance and CTA.' }
  ];

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-slate-950/20 backdrop-blur-sm z-40 transition-opacity"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 w-96 bg-slate-900 border-l border-slate-800 shadow-2xl z-50 flex flex-col transform animate-in slide-in-from-right duration-300">
        <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950/50">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <History className="w-5 h-5 text-primary-400" />
            Version History
          </h2>
          <button onClick={onClose} className="p-2 -mr-2 text-slate-400 hover:text-slate-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-4 relative">
          <div className="absolute left-8 top-8 bottom-8 w-px bg-slate-800" />
          
          {versions.map((v) => (
            <div key={v.id} className={clsx(
              "card relative p-4 pl-12 transition-colors",
              v.is_current ? "border-primary-500/50 bg-primary-500/5" : "hover:border-slate-700"
            )}>
              <div className={clsx(
                "absolute left-[-11px] top-6 w-6 h-6 rounded-full border-4 border-slate-900 flex items-center justify-center",
                v.is_current ? "bg-primary-500 text-slate-900" : "bg-slate-700 text-slate-400"
              )}>
                 {v.is_current ? <CheckCircle2 className="w-4 h-4" /> : <Clock className="w-3 h-3" />}
              </div>
              
              <div className="flex justify-between items-start mb-1">
                <h3 className="font-medium text-slate-200">{v.title}</h3>
                <span className="text-xs text-slate-500">{new Date(v.date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
              </div>
              <p className="text-sm text-slate-400 mb-3">{v.changes}</p>
              
              <div className="flex gap-2">
                <button className="btn-secondary text-xs py-1 px-2.5 h-auto">View Diff</button>
                {!v.is_current && (
                   <button className="btn-ghost text-primary-400 text-xs py-1 px-2 h-auto ml-auto">Restore</button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
