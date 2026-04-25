import React, { useState } from 'react';
import {
  Zap,
  Loader2,
  RefreshCw,
  AlertTriangle,
  Check,
  ArrowRight,
  Copy,
  Quote,
} from 'lucide-react';
import { toolsApi } from '../../services/api';
import toast from 'react-hot-toast';

interface HookTesterProps {
  scriptText: string;
  niche?: string;
  platform?: string;
  onApplyRewrite?: (text: string) => void;
}

const scoreColor = (score: number) => {
  if (score >= 7) return 'text-green-400';
  if (score >= 5) return 'text-yellow-400';
  return 'text-red-400';
};

const scoreBg = (score: number) => {
  if (score >= 7) return 'bg-green-400';
  if (score >= 5) return 'bg-yellow-400';
  return 'bg-red-400';
};

const scoreGradient = (score: number) => {
  if (score >= 7) return 'stroke-green-400';
  if (score >= 5) return 'stroke-yellow-400';
  return 'stroke-red-400';
};

const scoreGlow = (score: number) => {
  if (score >= 7) return 'drop-shadow-[0_0_8px_rgba(74,222,128,0.5)]';
  if (score >= 5) return 'drop-shadow-[0_0_8px_rgba(250,204,21,0.5)]';
  return 'drop-shadow-[0_0_8px_rgba(248,113,113,0.5)]';
};

/* ── Radial Gauge Component ────────────────────────────────── */
const RadialGauge: React.FC<{ score: number; size?: number }> = ({ score, size = 100 }) => {
  const strokeWidth = 6;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 10) * circumference;

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className={`-rotate-90 ${scoreGlow(score)}`}>
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth={strokeWidth}
        />
        {/* Score arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          className={scoreGradient(score)}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1)' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-display font-bold ${scoreColor(score)}`}>
          {score.toFixed(1)}
        </span>
        <span className="text-[9px] text-text-secondary uppercase tracking-widest">/10</span>
      </div>
    </div>
  );
};

export const HookTester: React.FC<HookTesterProps> = ({
  scriptText,
  niche,
  platform,
  onApplyRewrite,
}) => {
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const runTest = async () => {
    if (!scriptText?.trim()) {
      toast.error('No script text to analyze');
      return;
    }
    setLoading(true);
    setIsOpen(true);
    try {
      const data = await toolsApi.testHook(scriptText, niche, platform);
      setResult(data);
    } catch (e: any) {
      toast.error('Hook test failed');
    } finally {
      setLoading(false);
    }
  };

  const dimensions = result?.breakdown
    ? [
        { key: 'curiosity_gap', label: 'Curiosity Gap', icon: '🔍' },
        { key: 'emotional_trigger', label: 'Emotional Trigger', icon: '💥' },
        { key: 'specificity', label: 'Specificity', icon: '🎯' },
        { key: 'pattern_interrupt', label: 'Pattern Interrupt', icon: '⚡' },
        { key: 'relevance', label: 'Relevance', icon: '🧭' },
      ]
    : [];

  return (
    <div className="border border-white/5 bg-surface/30 rounded-2xl overflow-hidden transition-all duration-300">
      {/* Header */}
      <button
        onClick={() => (result ? setIsOpen(!isOpen) : runTest())}
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-accent">
          <Zap className="w-4 h-4" />
          Hook Tester
          {result && (
            <span className={`text-lg font-display font-bold ml-2 ${scoreColor(result.overall_score)}`}>
              {result.overall_score.toFixed(1)}/10
            </span>
          )}
        </div>
        {!result && !loading && (
          <span className="text-xs text-text-secondary px-3 py-1 bg-white/5 rounded-lg hover:bg-white/8 transition-colors">
            Test My Hook →
          </span>
        )}
        {loading && <Loader2 className="w-4 h-4 animate-spin text-accent" />}
      </button>

      {/* Results */}
      {isOpen && result && (
        <div className="p-5 pt-0 space-y-5 border-t border-white/5 animate-in">
          {/* Top Section: Gauge + Score Bars */}
          <div className="flex gap-6 items-start pt-4">
            {/* Radial Gauge */}
            <div className="flex-shrink-0">
              <RadialGauge score={result.overall_score} size={100} />
            </div>

            {/* Score Bars */}
            <div className="flex-1 space-y-2.5">
              {dimensions.map((dim) => {
                const score = result.breakdown[dim.key] || 0;
                return (
                  <div key={dim.key} className="space-y-0.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-text-secondary">
                        {dim.icon} {dim.label}
                      </span>
                      <span className={`font-semibold tabular-nums ${scoreColor(score)}`}>{score}</span>
                    </div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${scoreBg(score)}`}
                        style={{ width: `${score * 10}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Analyzed Hook Quote */}
          {result.hook_text && (
            <div className="p-4 bg-accent/5 border border-accent/10 rounded-xl relative">
              <Quote className="w-4 h-4 text-accent/30 absolute top-3 left-3" />
              <div className="pl-6 text-sm text-text-secondary leading-relaxed italic line-clamp-4">
                "{result.hook_text}"
              </div>
              <div className="mt-2 pl-6 text-[10px] text-text-secondary/50 uppercase tracking-widest">
                Analyzed Hook (~30 seconds)
              </div>
            </div>
          )}

          {/* Verdict */}
          {result.verdict && (
            <div className="p-3 bg-white/3 rounded-xl text-sm text-text-secondary">
              <AlertTriangle className="w-3.5 h-3.5 inline mr-1.5 text-yellow-400" />
              {result.verdict}
            </div>
          )}

          {/* Rewrites */}
          {result.rewrites?.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-semibold uppercase tracking-widest text-text-secondary">
                Suggested Rewrites
              </div>
              {result.rewrites.map((rw: any, i: number) => (
                <div
                  key={i}
                  className="p-3 border border-white/5 rounded-xl hover:border-accent/20 transition-all group"
                >
                  <div className="text-sm text-text-primary mb-2">"{rw.text}"</div>
                  <div className="flex items-center justify-between text-xs text-text-secondary">
                    <span className="flex-1">{rw.improvement}</span>
                    <span className={`font-semibold mr-3 ${scoreColor(rw.predicted_score)}`}>
                      {rw.predicted_score?.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex gap-2 mt-2.5">
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(rw.text);
                        toast.success('Copied rewrite');
                      }}
                      className="text-[10px] text-text-secondary hover:text-accent transition-colors flex items-center gap-1 px-2 py-1 rounded-md bg-white/5 hover:bg-white/8"
                    >
                      <Copy className="w-3 h-3" /> Copy
                    </button>
                    {onApplyRewrite && (
                      <button
                        onClick={() => {
                          onApplyRewrite(rw.text);
                          toast.success('Rewrite applied to instruction');
                        }}
                        className="text-[10px] text-accent hover:text-accent/80 transition-colors flex items-center gap-1 px-2 py-1 rounded-md bg-accent/10 hover:bg-accent/15"
                      >
                        <ArrowRight className="w-3 h-3" /> Apply
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Retest */}
          <button
            onClick={runTest}
            disabled={loading}
            className="text-xs text-text-secondary hover:text-accent transition-colors flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" /> Retest
          </button>
        </div>
      )}
    </div>
  );
};
