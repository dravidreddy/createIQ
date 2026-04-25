import React, { useState } from 'react';
import { Youtube, Search, Loader2, Target, MessageSquare, Zap, Clock, PlayCircle } from 'lucide-react';
import { toolsApi } from '../services/api';
import toast from 'react-hot-toast';

export default function CompetitorAnalysis() {
    const [url, setUrl] = useState('');
    const [analyzing, setAnalyzing] = useState(false);
    const [result, setResult] = useState<any>(null);

    const handleAnalyze = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!url.includes('youtube.com/') && !url.includes('youtu.be/')) {
            toast.error('Please enter a valid YouTube URL');
            return;
        }

        setAnalyzing(true);
        setResult(null);

        try {
            const data = await toolsApi.analyzeCompetitor(url);
            setResult(data);
            toast.success('Analysis complete!');
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to analyze competitor');
        } finally {
            setAnalyzing(false);
        }
    };

    return (
        <div className="workspace-container">
            <div className="flex flex-col gap-2 mb-8 text-center max-w-2xl mx-auto">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent/20 text-accent mb-4 mx-auto glow-accent">
                    <Youtube className="w-8 h-8" />
                </div>
                <h1 className="text-4xl font-display font-bold text-gradient">
                    Competitor Analysis
                </h1>
                <p className="text-text-secondary text-lg">
                    Paste a YouTube URL to reverse-engineer their script, extract their hooks, and steal their retention mechanics.
                </p>
            </div>

            <form onSubmit={handleAnalyze} className="max-w-3xl mx-auto mb-12">
                <div className="relative flex items-center">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <Search className="w-5 h-5 text-text-secondary" />
                    </div>
                    <input
                        type="url"
                        placeholder="https://www.youtube.com/watch?v=..."
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        className="w-full pl-12 pr-32 py-4 bg-surface border border-white/10 rounded-2xl text-lg focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/50 transition-all shadow-xl"
                        required
                    />
                    <div className="absolute inset-y-0 right-2 flex items-center">
                        <button
                            type="submit"
                            disabled={analyzing || !url}
                            className="btn-primary py-2 px-6 rounded-xl font-bold"
                        >
                            {analyzing ? (
                                <><Loader2 className="w-4 h-4 animate-spin mr-2 inline" /> Analyzing</>
                            ) : (
                                'Analyze'
                            )}
                        </button>
                    </div>
                </div>
                {analyzing && (
                    <div className="mt-4 text-center text-sm text-text-secondary animate-pulse flex items-center justify-center gap-2">
                        <Zap className="w-4 h-4 text-yellow-400" />
                        Fetching transcript and extracting narrative structure...
                    </div>
                )}
            </form>

            {result && (
                <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
                    {/* Top Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="glass p-6 rounded-2xl border-l-4 border-l-accent">
                            <h3 className="text-xs font-semibold uppercase tracking-widest text-text-secondary mb-2 flex items-center gap-2">
                                <Target className="w-4 h-4 text-accent" />
                                Core Message
                            </h3>
                            <p className="text-lg font-medium leading-relaxed">
                                {result.core_message}
                            </p>
                        </div>
                        <div className="glass p-6 rounded-2xl border-l-4 border-l-purple-500">
                            <h3 className="text-xs font-semibold uppercase tracking-widest text-text-secondary mb-2 flex items-center gap-2">
                                <PlayCircle className="w-4 h-4 text-purple-400" />
                                Pacing & Tone
                            </h3>
                            <p className="text-lg font-medium leading-relaxed text-purple-100">
                                {result.pacing_and_tone}
                            </p>
                        </div>
                    </div>

                    {/* The Hook */}
                    <div className="glass p-8 rounded-3xl relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                            <Zap className="w-32 h-32 text-yellow-400" />
                        </div>
                        <h2 className="text-xl font-display font-bold mb-6 flex items-center gap-3">
                            <div className="p-2 bg-yellow-500/20 text-yellow-400 rounded-xl">
                                <Zap className="w-5 h-5" />
                            </div>
                            The Hook (First 30 Seconds)
                        </h2>
                        
                        <div className="grid md:grid-cols-2 gap-8">
                            <div>
                                <div className="text-xs font-semibold uppercase tracking-widest text-text-secondary mb-3">
                                    Exact Transcript
                                </div>
                                <blockquote className="p-5 bg-white/5 border-l-2 border-white/10 rounded-r-2xl text-text-primary/90 font-medium italic leading-relaxed">
                                    "{result.hook_breakdown?.text}"
                                </blockquote>
                            </div>
                            <div>
                                <div className="text-xs font-semibold uppercase tracking-widest text-text-secondary mb-3">
                                    Psychological Strategy
                                </div>
                                <div className="p-5 bg-yellow-500/5 border border-yellow-500/20 rounded-2xl text-yellow-100/90 font-medium leading-relaxed">
                                    {result.hook_breakdown?.strategy}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="grid md:grid-cols-2 gap-6">
                        {/* Structure Timeline */}
                        <div className="glass p-8 rounded-3xl">
                            <h2 className="text-xl font-display font-bold mb-8 flex items-center gap-3">
                                <div className="p-2 bg-blue-500/20 text-blue-400 rounded-xl">
                                    <Clock className="w-5 h-5" />
                                </div>
                                Narrative Arc
                            </h2>
                            <div className="space-y-6 relative before:absolute before:inset-0 before:ml-2.5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-white/10 before:to-transparent">
                                {result.structure?.map((section: any, idx: number) => (
                                    <div key={idx} className="relative flex items-start gap-4">
                                        <div className="absolute left-0 w-5 h-5 rounded-full border-4 border-bg bg-blue-400 mt-1" />
                                        <div className="pl-8">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="text-xs font-mono px-2 py-0.5 bg-white/5 rounded text-text-secondary">
                                                    {section.timestamp}
                                                </span>
                                                <h4 className="font-semibold text-text-primary">
                                                    {section.section}
                                                </h4>
                                            </div>
                                            <p className="text-sm text-text-secondary leading-relaxed">
                                                {section.purpose}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Pattern Interrupts & CTA */}
                        <div className="space-y-6">
                            <div className="glass p-8 rounded-3xl">
                                <h2 className="text-xl font-display font-bold mb-6 flex items-center gap-3">
                                    <div className="p-2 bg-green-500/20 text-green-400 rounded-xl">
                                        <MessageSquare className="w-5 h-5" />
                                    </div>
                                    Pattern Interrupts
                                </h2>
                                <ul className="space-y-4">
                                    {result.pattern_interrupts?.map((interrupt: string, idx: number) => (
                                        <li key={idx} className="flex gap-3 text-sm text-text-secondary bg-white/3 p-4 rounded-xl border border-white/5">
                                            <span className="text-green-400 mt-0.5">✦</span>
                                            <span className="leading-relaxed">{interrupt}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            <div className="glass p-8 rounded-3xl border-t border-t-white/10">
                                <h2 className="text-xl font-display font-bold mb-4">The Ask (CTA)</h2>
                                <div className="space-y-3">
                                    <div className="flex items-center justify-between text-xs text-text-secondary">
                                        <span className="uppercase tracking-widest font-semibold">Placement</span>
                                        <span className="px-2 py-1 bg-white/5 rounded-lg">{result.call_to_action?.placement}</span>
                                    </div>
                                    <div className="p-4 bg-white/5 rounded-xl border border-white/10 font-medium italic text-text-primary/80">
                                        "{result.call_to_action?.text}"
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
