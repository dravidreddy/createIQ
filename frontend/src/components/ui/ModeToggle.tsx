import React from 'react';
import clsx from 'clsx';

export type CreatorMode = 'auto' | 'guided' | 'manual';

interface ModeToggleProps {
  mode: CreatorMode;
  onChange: (mode: CreatorMode) => void;
}

export const ModeToggle: React.FC<ModeToggleProps> = ({ mode, onChange }) => {
  const modes: { id: CreatorMode; label: string; desc: string }[] = [
    { id: 'auto', label: 'Auto', desc: 'Full automation' },
    { id: 'guided', label: 'Guided', desc: '2-3 checkpoints' },
    { id: 'manual', label: 'Manual', desc: 'Full control' },
  ];

  return (
    <div className="inline-flex p-1 bg-surface border border-white/5 rounded-xl shadow-inner">
      {modes.map((m) => (
        <button
          key={m.id}
          onClick={() => onChange(m.id)}
          className={clsx(
            'relative px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-300',
            mode === m.id
              ? 'text-white bg-accent shadow-glow'
              : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
          )}
        >
          {m.label}
          {mode === m.id && (
            <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 bg-white rounded-full animate-pulse" />
          )}
        </button>
      ))}
    </div>
  );
};
