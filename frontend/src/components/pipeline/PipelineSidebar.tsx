import { Lightbulb, FileText, Film, Edit3, TrendingUp, Check, Loader2, Play } from 'lucide-react';
import { clsx } from 'clsx';
import { useStreamingStore } from '../../store/streamingStore';

const STAGES = [
  { id: 'idea_discovery', label: 'Discover Ideas', icon: Lightbulb },
  { id: 'hook_generation', label: 'Hook Generation', icon: TrendingUp },
  { id: 'script_writing', label: 'Script Writing', icon: FileText },
  { id: 'structure', label: 'Screenplay Structure', icon: Film },
  { id: 'editing', label: 'Script Editing', icon: Edit3 },
  { id: 'strategy', label: 'Strategy & SEO', icon: TrendingUp },
];

interface Props {
  activeStage: string;
  completedStages: string[];
  onStageClick: (stage: string) => void;
  metadata?: { cost: number; tokens: { input: number; output: number } };
  onStartPipeline: () => void;
}

export function PipelineSidebar({ activeStage, completedStages, onStageClick, metadata, onStartPipeline }: Props) {
  const { status } = useStreamingStore();
  const isRunning = status === 'running';

  return (
    <div className="w-64 border-r border-slate-800 bg-slate-950/50 flex flex-col h-full shrink-0">
      <div className="p-4 border-b border-slate-800 flex flex-col gap-3">
         <button 
           onClick={onStartPipeline}
           disabled={isRunning}
           className="btn btn-primary w-full flex items-center justify-center gap-2 shadow-lg shadow-primary-500/20"
         >
           {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
           {isRunning ? 'Generating...' : 'Start Pipeline'}
         </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-1 py-6">
        {STAGES.map((stage) => {
          const isActive = stage.id === activeStage;
          const isCompleted = completedStages.includes(stage.id);
          const isPending = !isActive && !isCompleted;
          
          return (
            <button
              key={stage.id}
              onClick={() => (isCompleted || isActive) && onStageClick(stage.id)}
              disabled={isPending}
              className={clsx(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-left transition-all duration-200",
                isActive ? "bg-primary-500/10 text-primary-400 border border-primary-500/20" : "border border-transparent",
                isCompleted ? "text-slate-100 hover:bg-slate-800/50 cursor-pointer" : "",
                isPending ? "text-slate-600 cursor-not-allowed opacity-50" : ""
              )}
            >
              <div className={clsx(
                "w-6 h-6 rounded flex items-center justify-center",
                isActive ? "bg-primary-500/20" : "",
                isCompleted ? "bg-success-500/10 text-success-500" : ""
              )}>
                {isCompleted ? <Check className="w-4 h-4" /> : <stage.icon className="w-4 h-4" />}
              </div>
              <span className="font-medium flex-1 truncate">{stage.label}</span>
              {isActive && isRunning && <Loader2 className="w-3 h-3 animate-spin" />}
            </button>
          );
        })}
      </div>

      <div className="p-4 border-t border-slate-800 bg-slate-900/50">
        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Project Metadata</h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between text-slate-400">
            <span>Running Cost:</span>
            <span className="font-mono text-slate-300">
              ${((metadata?.cost || 0) / 100).toFixed(4)}
            </span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Tokens:</span>
            <span className="font-mono text-slate-300 flex gap-1">
              <span className="text-blue-400" title="Input">{metadata?.tokens.input || 0}</span> / 
              <span className="text-green-400" title="Output">{metadata?.tokens.output || 0}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
