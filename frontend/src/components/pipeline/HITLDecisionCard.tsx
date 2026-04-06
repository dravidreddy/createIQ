import { useState } from 'react';
import { Check, Edit2, RotateCw } from 'lucide-react';
import { useStreamingStore } from '../../store/streamingStore';
import { usePipelineStream } from '../../hooks/usePipelineStream';

export function HITLDecisionCard({ threadId }: { threadId: string }) {
  const { interruptContext, status } = useStreamingStore();
  const { resumePipeline } = usePipelineStream();
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (status !== 'interrupted' || !interruptContext) return null;

  const handleAction = async (action: 'approve' | 'edit' | 'regenerate') => {
    setIsSubmitting(true);
    try {
      await resumePipeline(threadId, action, interruptContext.stage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="card p-6 border-warning-500/50 bg-warning-500/5 shadow-2xl relative overflow-hidden animate-in fade-in slide-in-from-bottom-4">
      <div className="absolute top-0 left-0 w-full h-1 bg-warning-500/50" />
      
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-full bg-warning-500/20 text-warning-500 flex items-center justify-center shrink-0">
          <Edit2 className="w-5 h-5 ml-0.5" />
        </div>
        
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            Action Required
            <span className="text-xs bg-warning-500/20 text-warning-400 px-2 py-0.5 rounded-full font-mono">
              {interruptContext.stage}
            </span>
          </h3>
          <p className="text-slate-400 mt-1 mb-6 text-sm leading-relaxed">
            {interruptContext.message || "Review the generated content and choose how you would like to proceed."}
          </p>
          
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => handleAction('approve')}
              disabled={isSubmitting}
              className="btn bg-success-600 hover:bg-success-500 text-white border-transparent px-5"
            >
              <Check className="w-4 h-4 mr-2" />
              Approve Best
            </button>
            <button
              onClick={() => handleAction('regenerate')}
              disabled={isSubmitting}
              className="btn btn-secondary px-5"
            >
              <RotateCw className="w-4 h-4 mr-2" />
              Redo Stage
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
