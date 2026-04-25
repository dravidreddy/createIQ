import React from 'react';
import clsx from 'clsx';
import { Check, Dot } from 'lucide-react';

export type PipelineStage = 'research' | 'hook' | 'script' | 'edit' | 'output';

interface PipelineFlowProps {
  currentStage: PipelineStage;
  completedStages: PipelineStage[];
}

export const PipelineFlow: React.FC<PipelineFlowProps> = ({ currentStage, completedStages }) => {
  const stages: { id: PipelineStage; label: string }[] = [
    { id: 'research', label: 'Research' },
    { id: 'hook', label: 'Hook' },
    { id: 'script', label: 'Script' },
    { id: 'edit', label: 'Edit' },
    { id: 'output', label: 'Output' },
  ];

  return (
    <div className="flex items-center justify-center gap-12 py-8 overflow-x-auto scrollbar-hide">
      {stages.map((stage, index) => {
        const isActive = currentStage === stage.id;
        const isCompleted = completedStages.includes(stage.id);
        const isPast = stages.findIndex(s => s.id === currentStage) > index;
        
        return (
          <div key={stage.id} className="flex items-center gap-4 group">
            <div className="flex flex-col items-center gap-2">
              <div className="relative">
                {/* Glowing Aura for Active Stage */}
                {isActive && (
                  <div className="absolute inset-0 bg-accent rounded-full blur-md opacity-40 animate-pulse" />
                )}
                <div
                  className={clsx(
                    'relative z-10 w-8 h-8 rounded-full border-2 flex items-center justify-center transition-all duration-500',
                    isActive 
                      ? 'border-accent bg-accent/20 shadow-glow text-accent' 
                      : isCompleted || isPast
                        ? 'border-accent bg-accent text-white'
                        : 'border-white/10 bg-transparent text-text-secondary'
                  )}
                >
                  {isCompleted || isPast ? (
                    <Check className="w-4 h-4 animate-in zoom-in" />
                  ) : isActive ? (
                    <Dot className="w-6 h-6 animate-pulse" />
                  ) : (
                    <span className="text-xs font-mono">{index + 1}</span>
                  )}
                </div>
              </div>
              <span
                className={clsx(
                  'text-xs font-medium tracking-widest uppercase transition-colors duration-300',
                  isActive ? 'text-accent' : 'text-text-secondary group-hover:text-text-primary'
                )}
              >
                {stage.label}
              </span>
            </div>
            
            {index < stages.length - 1 && (
              <div className={clsx(
                'w-16 h-[1px] -mt-6 transition-all duration-700',
                isPast || isCompleted ? 'bg-accent' : 'bg-white/10'
              )} />
            )}
          </div>
        );
      })}
    </div>
  );
};
