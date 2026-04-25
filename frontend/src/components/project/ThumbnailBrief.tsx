import React, { useState } from 'react';
import {
  Image,
  Loader2,
  Copy,
  Check,
  Palette,
  Type,
  Layout,
  Smile,
  Eye,
} from 'lucide-react';
import { toolsApi } from '../../services/api';
import toast from 'react-hot-toast';

interface ThumbnailBriefProps {
  scriptText: string;
  hookText?: string;
  topic?: string;
}

export const ThumbnailBrief: React.FC<ThumbnailBriefProps> = ({
  scriptText,
  hookText,
  topic,
}) => {
  const [brief, setBrief] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const generateBrief = async () => {
    if (!scriptText?.trim()) {
      toast.error('No script to generate thumbnail from');
      return;
    }
    setLoading(true);
    setIsOpen(true);
    try {
      const data = await toolsApi.generateThumbnailBrief(scriptText, hookText, topic);
      setBrief(data);
    } catch (e: any) {
      toast.error('Thumbnail brief generation failed');
    } finally {
      setLoading(false);
    }
  };

  const copyBrief = () => {
    if (!brief) return;
    const text = `THUMBNAIL BRIEF
Primary Text: ${brief.primary_text}
${brief.secondary_text ? `Secondary Text: ${brief.secondary_text}` : ''}
Expression: ${brief.expression}
Color Scheme: ${brief.color_scheme}
Layout: ${brief.layout}
Elements: ${brief.elements?.join(', ')}
Style: ${brief.style_reference}
Emotional Hook: ${brief.emotional_hook}
Contrast Tip: ${brief.contrast_tip}`;

    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success('Brief copied');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-white/5 bg-surface/30 rounded-2xl overflow-hidden transition-all duration-300">
      {/* Header */}
      <button
        onClick={() => (brief ? setIsOpen(!isOpen) : generateBrief())}
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-purple-400">
          <Image className="w-4 h-4" />
          Thumbnail Brief
          {brief && <Check className="w-3.5 h-3.5 text-green-400 ml-1" />}
        </div>
        {!brief && !loading && (
          <span className="text-xs text-text-secondary px-3 py-1 bg-white/5 rounded-lg">
            Generate →
          </span>
        )}
        {loading && <Loader2 className="w-4 h-4 animate-spin text-purple-400" />}
      </button>

      {/* Brief Content */}
      {isOpen && brief && (
        <div className="p-4 pt-0 space-y-4 border-t border-white/5 animate-in">
          {/* Primary Text — Hero */}
          <div className="text-center py-4 px-6 bg-gradient-to-br from-purple-500/10 to-accent/10 rounded-xl border border-white/5">
            <div className="text-2xl font-display font-bold text-white">
              "{brief.primary_text}"
            </div>
            {brief.secondary_text && (
              <div className="text-sm text-text-secondary mt-1">{brief.secondary_text}</div>
            )}
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-white/3 rounded-xl">
              <div className="flex items-center gap-1.5 text-xs text-text-secondary mb-1">
                <Smile className="w-3.5 h-3.5" /> Expression
              </div>
              <div className="text-sm font-medium capitalize">{brief.expression}</div>
            </div>

            <div className="p-3 bg-white/3 rounded-xl">
              <div className="flex items-center gap-1.5 text-xs text-text-secondary mb-1">
                <Eye className="w-3.5 h-3.5" /> Emotion
              </div>
              <div className="text-sm font-medium capitalize">{brief.emotional_hook}</div>
            </div>

            <div className="p-3 bg-white/3 rounded-xl col-span-2">
              <div className="flex items-center gap-1.5 text-xs text-text-secondary mb-1">
                <Palette className="w-3.5 h-3.5" /> Color Scheme
              </div>
              <div className="text-sm">{brief.color_scheme}</div>
            </div>

            <div className="p-3 bg-white/3 rounded-xl col-span-2">
              <div className="flex items-center gap-1.5 text-xs text-text-secondary mb-1">
                <Layout className="w-3.5 h-3.5" /> Layout
              </div>
              <div className="text-sm">{brief.layout}</div>
            </div>
          </div>

          {/* Elements */}
          {brief.elements?.length > 0 && (
            <div>
              <div className="text-xs text-text-secondary mb-2 font-semibold uppercase tracking-widest">
                Visual Elements
              </div>
              <div className="flex flex-wrap gap-2">
                {brief.elements.map((el: string, i: number) => (
                  <span
                    key={i}
                    className="text-xs px-2.5 py-1 bg-white/5 border border-white/10 rounded-lg"
                  >
                    {el}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Style Reference + Contrast Tip */}
          {brief.style_reference && (
            <div className="p-3 bg-purple-500/5 border border-purple-500/10 rounded-xl text-sm">
              <Type className="w-3.5 h-3.5 inline mr-1.5 text-purple-400" />
              <span className="text-text-secondary">Style:</span>{' '}
              {brief.style_reference}
            </div>
          )}

          {brief.contrast_tip && (
            <div className="p-3 bg-yellow-500/5 border border-yellow-500/10 rounded-xl text-sm">
              💡 <span className="text-text-secondary">Pro tip:</span>{' '}
              {brief.contrast_tip}
            </div>
          )}

          {/* Copy */}
          <button
            onClick={copyBrief}
            className="btn-secondary py-1.5 px-3 text-xs gap-2 w-full justify-center"
          >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied!' : 'Copy Full Brief'}
          </button>
        </div>
      )}
    </div>
  );
};
