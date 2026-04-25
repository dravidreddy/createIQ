import React, { useState } from 'react';
import { 
  ChevronDown, 
  ChevronUp, 
  Copy, 
  Check, 
  Sparkles,
  Share2,
  FileText,
  Target,
  Zap
} from 'lucide-react';
import toast from 'react-hot-toast';

interface OutputEditorProps {
  content: string;
  hooks?: string[];
  strategy?: string;
  variations?: string[];
}

export const OutputEditor: React.FC<OutputEditorProps> = ({ 
  content, 
  hooks = [], 
  strategy, 
  variations = [] 
}) => {
  const [isStrategyOpen, setIsStrategyOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-12 max-w-4xl mx-auto animate-in">
      {/* Strategy / Context (Progressive Disclosure) */}
      {strategy && (
        <div className="border border-white/5 bg-surface/30 rounded-2xl overflow-hidden transition-all duration-500">
          <button 
            onClick={() => setIsStrategyOpen(!isStrategyOpen)}
            className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors text-text-secondary"
          >
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest">
              <Target className="w-4 h-4" />
              Content Strategy
            </div>
            {isStrategyOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          
          {isStrategyOpen && (
            <div className="p-6 pt-0 text-sm text-text-secondary border-t border-white/5 transition-all animate-in slide-in">
              {strategy}
            </div>
          )}
        </div>
      )}

      {/* Main Writing Interface */}
      <div className="relative group">
        <div className="absolute -left-12 top-0 py-4 opacity-0 group-hover:opacity-100 transition-opacity">
           <Zap className="w-6 h-6 text-accent/20" />
        </div>
        
        <div className="space-y-6">
          <div className="flex items-baseline justify-between mb-8">
            <h2 className="text-3xl font-display font-bold text-gradient">Final Script</h2>
            <div className="flex gap-2">
              <button 
                onClick={handleCopy}
                className="btn-secondary py-1.5 px-3 text-xs gap-2"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
              <button className="btn-primary py-1.5 px-3 text-xs gap-2">
                <Share2 className="w-3.5 h-3.5" />
                Publish
              </button>
            </div>
          </div>

          <div className="prose prose-invert prose-p:text-text-primary prose-p:leading-relaxed prose-p:text-lg max-w-none">
            <textarea
              value={content}
              readOnly
              className="w-full bg-transparent border-none focus:ring-0 text-xl leading-relaxed min-h-[400px] resize-none scrollbar-hide text-text-primary"
            />
          </div>
        </div>
      </div>

      {/* Expandable Sections (Hooks & Variations) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {hooks.length > 0 && (
          <div className="card-minimal space-y-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-accent">
              <Sparkles className="w-4 h-4" />
              Hook Variations
            </div>
            <ul className="space-y-3">
              {hooks.map((hook, i) => (
                <li key={i} className="text-sm text-text-secondary p-3 bg-white/5 rounded-lg hover:bg-white/5 transition-colors cursor-pointer group">
                  <span className="text-accent/40 mr-2 font-mono">{i + 1}.</span>
                  {hook}
                </li>
              ))}
            </ul>
          </div>
        )}

        {variations.length > 0 && (
          <div className="card-minimal space-y-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-text-secondary">
              <FileText className="w-4 h-4" />
              Alternative Angles
            </div>
            <ul className="space-y-3">
              {variations.map((v, i) => (
                <li key={i} className="text-sm text-text-secondary p-3 border border-white/5 rounded-lg hover:border-white/10 transition-colors cursor-pointer capitalize">
                  {v}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
