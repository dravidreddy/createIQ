import React from 'react';
import clsx from 'clsx';
import { Bot, Zap, UserCheck } from 'lucide-react';

export type ExecutionMode = 'auto' | 'guided' | 'manual';

interface ModeSelectorProps {
  selected: ExecutionMode;
  onChange: (mode: ExecutionMode) => void;
}

export const ModeSelector: React.FC<ModeSelectorProps> = ({ selected, onChange }) => {
  const modes: { id: ExecutionMode; label: string; description: string; icon: any }[] = [
    { 
        id: 'auto', 
        label: 'Auto', 
        description: 'Fully autonomous. No interrupts.',
        icon: Zap
    },
    { 
        id: 'guided', 
        label: 'Guided', 
        description: 'Key checkpoints only (Ideas & Final Review).',
        icon: UserCheck
    },
    { 
        id: 'manual', 
        label: 'Manual', 
        description: 'Full control. Interruption at every stage.',
        icon: Bot
    },
  ];

  return (
    <div className="flex bg-surface/80 p-1.5 rounded-2xl border border-white/5 gap-1 shadow-inner">
      {modes.map((m) => {
        const Icon = m.icon;
        const isSelected = selected === m.id;
        
        return (
          <button
            key={m.id}
            onClick={() => onChange(m.id)}
            title={m.description}
            className={clsx(
              'flex items-center gap-2 px-3 py-1.5 rounded-xl border text-[10px] font-mono uppercase tracking-[0.1em] transition-all duration-300',
              isSelected 
                ? 'bg-accent/10 border-accent/20 text-accent shadow-glow' 
                : 'bg-transparent border-transparent text-text-secondary hover:text-text-primary hover:bg-white/5'
            )}
          >
            <Icon className={clsx('w-3.5 h-3.5', isSelected && 'animate-pulse')} />
            {m.label}
          </button>
        );
      })}
    </div>
  );
};
