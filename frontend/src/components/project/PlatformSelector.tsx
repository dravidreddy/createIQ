import React from 'react';
import clsx from 'clsx';
import { Youtube, Instagram, Twitter, Linkedin, Music2 } from 'lucide-react';

export type Platform = 'youtube' | 'instagram' | 'twitter' | 'linkedin' | 'tiktok';

interface PlatformSelectorProps {
  selected: Platform;
  onChange: (platform: Platform) => void;
}

export const PlatformSelector: React.FC<PlatformSelectorProps> = ({ selected, onChange }) => {
  const platforms: { id: Platform; icon: any; label: string }[] = [
    { id: 'youtube', icon: Youtube, label: 'YouTube' },
    { id: 'instagram', icon: Instagram, label: 'Instagram' },
    { id: 'twitter', icon: Twitter, label: 'X / Twitter' },
    { id: 'tiktok', icon: Music2, label: 'TikTok' },
    { id: 'linkedin', icon: Linkedin, label: 'LinkedIn' },
  ];

  return (
    <div className="flex gap-2">
      {platforms.map((p) => {
        const Icon = p.icon;
        const isSelected = selected === p.id;
        
        return (
          <button
            key={p.id}
            onClick={() => onChange(p.id)}
            title={p.label}
            className={clsx(
              'p-2.5 rounded-xl border transition-all duration-300 group',
              isSelected 
                ? 'bg-accent/10 border-accent/30 text-accent shadow-glow' 
                : 'bg-surface border-white/5 text-text-secondary hover:text-text-primary hover:border-white/10'
            )}
          >
            <Icon className={clsx(
              'w-5 h-5 transition-transform duration-300',
              isSelected ? 'scale-110' : 'group-hover:scale-105'
            )} />
          </button>
        );
      })}
    </div>
  );
};
