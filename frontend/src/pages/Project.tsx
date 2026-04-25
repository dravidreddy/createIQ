import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useProjectStore } from '../store/projectStore';
import { useStreamingStore, createMsgId } from '../store/streamingStore';
import { usePipelineStream } from '../hooks/usePipelineStream';
import { useInactivityTimeout } from '../hooks/useInactivityTimeout';
import { pipelineApi } from '../services/api';
import { 
  ArrowLeft, 
  Sparkles, 
  Loader2, 
  ChevronRight, 
  History,
  Zap,
  Play,
  Square,
  Coins
} from 'lucide-react';
import toast from 'react-hot-toast';
import { PipelineFlow, PipelineStage } from '../components/pipeline/PipelineFlow';
import { ChatTimeline } from '../components/pipeline/ChatTimeline';
import { PlatformSelector, Platform } from '../components/project/PlatformSelector';
import { ModeSelector, ExecutionMode } from '../components/project/ModeSelector';
import { OutputEditor } from '../components/project/OutputEditor';
import { MicButton } from '../components/ui/MicButton';
import { VersionHistory } from '../components/project/VersionHistory';
import { HookTester } from '../components/project/HookTester';
import { ThumbnailBrief } from '../components/project/ThumbnailBrief';
import { PricingModal } from '../components/billing/PricingModal';
import { useAuthStore } from '../store/authStore';

export default function Project() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { currentProject, isLoading, fetchProject, updateProject } = useProjectStore();
    const { status, streamedContent, threadId, activeAgent, interruptContext } = useStreamingStore();
    const { startPipeline, resumePipeline, stopStream, checkPipelineStatus } = usePipelineStream();

    // Pause pipeline streams after 10 minutes of user inactivity
    useInactivityTimeout();

    const [searchParams] = useSearchParams();

    const [platform, setPlatform] = useState<Platform>(() => {
        const p = searchParams.get('platform');
        return (p as Platform) || 'youtube';
    });
    const [mode, setMode] = useState<ExecutionMode>(() => {
        const m = searchParams.get('mode');
        return (m as ExecutionMode) || 'auto';
    });
    const [displayContent, setDisplayContent] = useState('');
    const [instruction, setInstruction] = useState('');
    const contentRef = useRef('');
    const [historyOpen, setHistoryOpen] = useState(false);
    const [pricingOpen, setPricingOpen] = useState(false);
    const { user } = useAuthStore();

    useEffect(() => {
        if (id) {
            fetchProject(id).catch(() => {
                toast.error('Failed to load project');
                navigate('/dashboard');
            });
            // Only check pipeline status if there's a real thread from a previous session
            if (threadId) {
                checkPipelineStatus(threadId).catch(console.error);
            }
        }
    }, [id]);

    // Buffered Streaming Effect
    useEffect(() => {
        if (status === 'running' && streamedContent.length > contentRef.current.length) {
            const nextChunk = streamedContent.slice(contentRef.current.length);
            contentRef.current = streamedContent;
            
            let i = 0;
            const interval = setInterval(() => {
                if (i < nextChunk.length) {
                    setDisplayContent(prev => prev + nextChunk[i]);
                    i++;
                } else {
                    clearInterval(interval);
                }
            }, 10); 
            return () => clearInterval(interval);
        } else if (status !== 'running') {
            let safeContent = streamedContent || currentProject?.generated_script || '';
            if (typeof safeContent !== 'string') {
                try { safeContent = JSON.stringify(safeContent, null, 2); } catch { safeContent = String(safeContent); }
            }
            setDisplayContent(safeContent);
            contentRef.current = safeContent;
        }
    }, [streamedContent, status, currentProject?.generated_script]);

    if (isLoading && !currentProject) {
        return (
            <div className="flex h-screen items-center justify-center bg-bg">
                <Loader2 className="w-8 h-8 animate-spin text-accent" />
            </div>
        );
    }

    if (!currentProject) return null;

    const currentStage = mapStatusToStage(currentProject.status, status, activeAgent, interruptContext?.stage);
    const completedStages = (currentProject.completed_stages || []) as PipelineStage[];

    const { addMessage } = useStreamingStore();

    const handleHitlSelect = async (stage: string, item: any) => {
        if (!threadId) return;
        try {
            await resumePipeline(threadId, 'approve', stage, { selected_content: item });
            toast.success('Selection confirmed');
        } catch (err) {
            toast.error('Failed to confirm selection');
        }
    };

    const handleStart = async (overrideTopic?: string) => {
        if (!id) return;
        const platformLabels: Record<Platform, string> = {
            youtube: 'YouTube',
            instagram: 'Instagram Reels',
            twitter: 'Twitter/X',
            linkedin: 'LinkedIn',
            tiktok: 'TikTok',
        };
        const selectedPlatform = platformLabels[platform];

        const topicToUse = overrideTopic || currentProject.topic || 'Start pipeline';

        // Add user prompt to chat timeline
        addMessage({
            id: createMsgId(),
            role: 'user',
            type: 'prompt',
            content: topicToUse,
            timestamp: Date.now(),
        });

        try {
            await startPipeline(id, topicToUse, { 
                niche: currentProject.niche || 'general',
                platforms: [selectedPlatform],
                platform: selectedPlatform,
                execution_mode: mode
            });
        } catch (err: any) {
            if (err?.response?.status === 402) {
                toast.error('Insufficient credits');
                setPricingOpen(true);
            } else {
                toast.error('Failed to start pipeline');
            }
        }
    };

    const handleStop = async () => {
        // Abort SSE stream immediately
        stopStream();
        useStreamingStore.getState().setStatus('done');
        // Tell backend to halt
        if (threadId) {
            try {
                await pipelineApi.stop(threadId);
            } catch (e) {
                console.error('Stop failed:', e);
            }
        }
        toast.success('Pipeline stopped');
    };

    const handleFeedback = async (text?: string | React.KeyboardEvent) => {
        // text could be event if called directly from onClick/onKeyDown improperly, so we safeguard it.
        const feedbackStr = typeof text === 'string' ? text : instruction;
        const feedback = feedbackStr.trim();

        if (status === 'idle' || status === 'done') {
            if (feedback) {
                await handleStart(feedback);
            } else {
                await handleStart();
            }
            setInstruction('');
            return;
        }

        if (!feedback || !threadId) return;

        // Add user message to chat timeline
        addMessage({
            id: createMsgId(),
            role: 'user',
            type: 'prompt',
            content: feedback,
            timestamp: Date.now(),
        });
        setInstruction('');

        try {
            const stageToResume = status === 'interrupted' ? (interruptContext?.stage || currentStage) : currentStage;
            await resumePipeline(threadId, 'edit', stageToResume, { feedback });
        } catch (err) {
            toast.error('Failed to send instruction');
        }
    };

    const ideasToRender = status === 'interrupted' && interruptContext?.stage === 'idea_selection' ? interruptContext.data : currentProject.discovered_ideas;
    const hasResearchContent = currentStage === 'research' && ideasToRender && ideasToRender.length > 0;
    const hasHookContent = currentStage === 'hook' && status === 'interrupted' && interruptContext?.stage === 'hook_selection' && interruptContext.data;
    const hasScriptContent = (currentStage === 'script' || currentStage === 'edit' || currentStage === 'output') && displayContent;
    const hasRightColumnContent = hasResearchContent || hasHookContent || hasScriptContent;

    return (
        <div className="min-h-screen bg-bg flex flex-col pt-16 pb-32">
            {/* Minimal Header */}
            <header className="fixed top-0 left-0 right-0 h-16 border-b border-white/5 bg-bg/80 backdrop-blur-xl z-50 px-6 flex items-center justify-between">
                <div className="flex items-center gap-6">
                    <button onClick={() => navigate('/dashboard')} className="p-2 -ml-2 text-text-secondary hover:text-text-primary transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div className="h-4 w-[1px] bg-white/10" />
                    <div className="flex items-center gap-3">
                        <InlineEditTitle 
                            initialTitle={typeof currentProject.title === 'string' ? currentProject.title : 'Untitled Project'}
                            onSave={async (newTitle) => {
                                if (newTitle !== currentProject.title) {
                                    await updateProject(currentProject.id, { title: newTitle })
                                    toast.success('Project renamed')
                                }
                            }}
                        />
                        <ChevronRight className="w-4 h-4 text-text-secondary" />
                        <span className="text-xs text-text-secondary font-mono uppercase tracking-wider">{currentProject.status}</span>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <ModeSelector selected={mode} onChange={setMode} />
                    <div className="h-6 w-[1px] bg-white/10 mx-2" />
                    <PlatformSelector selected={platform} onChange={setPlatform} />
                    <div className="h-6 w-[1px] bg-white/10 mx-2" />
                    {/* Credit Display */}
                    <button
                        onClick={() => setPricingOpen(true)}
                        className="flex items-center gap-2 py-1.5 px-3 text-xs font-medium rounded-xl bg-accent/10 border border-accent/20 text-accent hover:bg-accent/20 transition-all"
                    >
                        <Coins className="w-3.5 h-3.5" />
                        {user?.credits ?? 0}
                        <span className="text-text-secondary">credits</span>
                    </button>
                    <div className="h-6 w-[1px] bg-white/10 mx-2" />
                    <button 
                        onClick={() => setHistoryOpen(true)}
                        className="btn-secondary py-1.5 px-3 text-xs gap-2"
                    >
                        <History className="w-4 h-4" />
                        Versions
                    </button>
                    {status === 'idle' || status === 'done' ? (
                        <button 
                            onClick={() => handleStart()} 
                            data-testid="project-execute-btn"
                            className="btn-primary py-1.5 px-4 text-xs gap-2 shadow-glow animate-pulse hover:animate-none"
                        >
                            <Play className="w-3.5 h-3.5 fill-current" />
                            Execute
                        </button>
                    ) : null}
                </div>
            </header>

            {/* Core Pipeline Navigation */}
            <div className="sticky top-16 bg-bg/50 backdrop-blur-sm border-b border-white/5 z-40">
                <PipelineFlow currentStage={currentStage} completedStages={completedStages} />
            </div>

            {/* Main Workspace */}
            <main className="flex-1 workspace-container relative px-6">
                
                {/* Active Stage Overlay */}
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full pointer-events-none overflow-hidden -z-10">
                    <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-accent/5 rounded-full blur-[120px] animate-pulse" />
                </div>

                {status === 'idle' && !currentProject.discovered_ideas?.length && !displayContent ? (
                    /* Hero Empty State */
                    <div className="flex flex-col items-center justify-center h-[50vh] animate-in zoom-in duration-700">
                        <div className="w-20 h-20 bg-accent/20 rounded-full flex items-center justify-center mb-6 shadow-glow">
                            <Sparkles className="w-10 h-10 text-accent" />
                        </div>
                        <h1 className="text-4xl font-display font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">CreatorIQ Pipeline</h1>
                        <p className="text-text-secondary text-lg mb-8 text-center max-w-md">The most advanced AI engine for creating viral video concepts and scripts.</p>
                        <button 
                            onClick={() => handleStart()} 
                            className="btn-primary py-3 px-8 text-sm gap-2 shadow-glow animate-pulse hover:animate-none"
                        >
                            <Play className="w-4 h-4 fill-current" />
                            Start Pipeline
                        </button>
                    </div>
                ) : (
                    /* Split View Layout */
                    <div className="lg:flex lg:gap-8 animate-in slide-up h-[calc(100vh-16rem)]">
                        {/* Left Column: Chat Timeline */}
                        <div className={`w-full ${hasRightColumnContent ? 'lg:w-[35%]' : 'lg:w-[60%] mx-auto'} flex flex-col bg-surface/30 rounded-[2rem] border border-white/5 shadow-2xl overflow-hidden h-full transition-all duration-500`}>
                            <div className="p-4 border-b border-white/5 bg-surface/50 backdrop-blur flex items-center gap-3">
                                <div className="w-2 h-2 rounded-full bg-accent animate-pulse shadow-[0_0_8px_rgba(var(--color-accent),0.8)]" />
                                <span className="text-xs font-mono uppercase tracking-widest text-text-secondary">Activity Feed</span>
                            </div>
                            <ChatTimeline />
                        </div>

                        {/* Right Column: Results */}
                        {hasRightColumnContent && (
                        <div className="w-full lg:w-[65%] flex flex-col overflow-y-auto h-full pr-4 pb-32 scrollbar-hide">
                            {/* Research Stage - Idea Cards */}
                            {currentStage === 'research' && (
                                (() => {
                                    if (!ideasToRender || ideasToRender.length === 0) return null;

                                    return (
                                        <div className="space-y-8 animate-in fade-in duration-700">
                                            <div className="flex items-center gap-3">
                                                <Zap className="w-5 h-5 text-accent" />
                                                <h2 className="text-xl font-display font-bold uppercase tracking-widest text-text-secondary">Viral Concepts</h2>
                                            </div>
                                            <div className="grid gap-6 sm:grid-cols-2">
                                                {ideasToRender.map((idea: any, i: number) => (
                                                    <div 
                                                        key={i} 
                                                        onClick={() => handleHitlSelect('idea_selection', idea)}
                                                        className="card-minimal group cursor-pointer border border-transparent hover:border-accent/20 animate-in slide-up"
                                                        style={{ animationDelay: `${i * 150}ms` }}
                                                    >
                                                        <h3 className="font-semibold text-lg mb-2 group-hover:text-accent transition-colors">
                                                            {typeof idea.title === 'string' ? idea.title : JSON.stringify(idea.title)}
                                                        </h3>
                                                        <p className="text-sm text-text-secondary line-clamp-3 mb-4">
                                                            {typeof idea.description === 'string' ? idea.description : JSON.stringify(idea.description)}
                                                        </p>
                                                        <div className="flex items-center gap-2">
                                                            <span className="badge-minimal border-accent/30 text-accent">9.2 Viral Potential</span>
                                                            <span className="text-[10px] text-text-secondary font-mono">
                                                                {typeof idea.unique_angle === 'string' ? idea.unique_angle : JSON.stringify(idea.unique_angle)}
                                                            </span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    );
                                })()
                            )}

                            {/* Hook Stage - Hook Cards */}
                            {currentStage === 'hook' && status === 'interrupted' && interruptContext?.stage === 'hook_selection' && interruptContext.data && (
                                <div className="space-y-8 animate-in fade-in duration-700">
                                    <div className="flex items-center gap-3">
                                        <Sparkles className="w-5 h-5 text-accent" />
                                        <h2 className="text-xl font-display font-bold uppercase tracking-widest text-text-secondary">Select a Hook</h2>
                                    </div>
                                    <div className="grid gap-4">
                                        {interruptContext.data.map((hook: any, i: number) => {
                                            const hookType = typeof hook.hook_type === 'string' ? hook.hook_type : (typeof hook.type === 'string' ? hook.type : 'Variant');
                                            const hookContent = typeof hook.script_content === 'string' ? hook.script_content : (typeof hook.content === 'string' ? hook.content : JSON.stringify(hook));
                                            const hookWhy = typeof hook.psychological_trigger === 'string' ? hook.psychological_trigger : (typeof hook.reason === 'string' ? hook.reason : 'Grabs attention');

                                            return (
                                                <div 
                                                    key={i} 
                                                    onClick={() => handleHitlSelect('hook_selection', hook)}
                                                    className="card-minimal p-6 group cursor-pointer border border-transparent hover:border-accent/20 animate-in slide-up flex flex-col gap-3"
                                                    style={{ animationDelay: `${i * 150}ms` }}
                                                >
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-xs font-mono text-text-secondary uppercase tracking-wider">Option {i + 1}</span>
                                                        <span className="badge-minimal border-accent/30 text-accent">{hookType}</span>
                                                    </div>
                                                    <p className="text-base text-text-primary font-medium leading-relaxed">
                                                        {hookContent}
                                                    </p>
                                                    <div className="text-xs text-text-secondary mt-2">
                                                        <strong className="text-text-primary/70">Why it works:</strong> {hookWhy}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* Scripting / Output Stage View */}
                            {(currentStage === 'script' || currentStage === 'edit' || currentStage === 'output') && displayContent && (
                                <div className="space-y-8 animate-in fade-in duration-700">
                                     <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <Sparkles className="w-5 h-5 text-accent" />
                                            <h2 className="text-xl font-display font-bold uppercase tracking-widest text-text-secondary">AI Scripting</h2>
                                        </div>
                                        {status === 'running' && (
                                            <div className="flex items-center gap-2 text-[10px] font-mono text-accent uppercase tracking-tighter">
                                                <div className="w-1.5 h-1.5 bg-accent rounded-full animate-ping" />
                                                Streaming Output
                                            </div>
                                        )}
                                    </div>

                                    {currentStage === 'output' ? (
                                        <OutputEditor 
                                            content={displayContent}
                                            hooks={[]}
                                            strategy={''}
                                        />
                                    ) : (
                                        <div className="relative p-8 bg-surface/50 border border-white/5 rounded-[2rem] shadow-2xl">
                                            <div className="prose prose-invert prose-lg max-w-none">
                                                <pre className="whitespace-pre-wrap font-sans text-xl leading-relaxed text-text-primary/90">
                                                    {displayContent}
                                                    {status === 'running' && <span className="inline-block w-2 h-6 bg-accent ml-1 animate-pulse" />}
                                                </pre>
                                            </div>
                                        </div>
                                    )}

                                    {status !== 'running' && (
                                        <div className="space-y-4">
                                            <HookTester
                                                scriptText={displayContent}
                                                niche={currentProject?.niche || ''}
                                                platform={platform}
                                                onApplyRewrite={(text) => setInstruction(text)}
                                            />
                                            <ThumbnailBrief 
                                                scriptText={displayContent}
                                                hookText=""
                                                topic={currentProject?.topic || ''}
                                            />
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                        )}
                    </div>
                )}
            </main>

            {/* Instruction Bar (Fixed Bottom) */}
            <div className="fixed bottom-8 left-1/2 -translate-x-1/2 w-full max-w-[700px] px-6 z-50">
                <div className="relative flex items-center p-3 bg-elevated/80 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden group">
                    <div className="absolute inset-0 pointer-events-none bg-gradient-to-r from-accent/5 to-transparent opacity-0 group-focus-within:opacity-100 transition-opacity" />
                    <input 
                        value={instruction}
                        onChange={(e) => setInstruction(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleFeedback()}
                        placeholder={`Tell AI to refine the ${currentStage}...`}
                        className="flex-1 bg-transparent border-none focus:ring-0 focus:outline-none text-base font-medium px-4 placeholder:text-text-secondary/50"
                        data-testid="pipeline-instruction"
                    />
                    <div className="flex items-center gap-3 pr-2">
                        <MicButton 
                            onTranscription={(text) => setInstruction(text)} 
                            currentText={instruction}
                            disabled={status === 'running'} 
                        />
                        {(status === 'running' || status === 'interrupted') && (
                            <button 
                                onClick={handleStop}
                                className="p-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl hover:bg-red-500/20 transition-all animate-in fade-in zoom-in"
                                title="Stop Pipeline"
                            >
                                <Square className="w-5 h-5 fill-current" />
                            </button>
                        )}
                        <button 
                            onClick={() => handleFeedback()}
                            disabled={!instruction.trim() && status !== 'idle' && status !== 'done'}
                            className="p-3 bg-accent text-bg rounded-xl hover:bg-accent-hover transition-all disabled:opacity-30"
                        >
                            <Sparkles className="w-5 h-5 fill-current" />
                        </button>
                    </div>
                </div>
            </div>

            {/* Version History Panel */}
            {id && (
                <VersionHistory 
                    projectId={id} 
                    isOpen={historyOpen} 
                    onClose={() => setHistoryOpen(false)} 
                />
            )}

            {/* Pricing Modal */}
            <PricingModal 
                isOpen={pricingOpen} 
                onClose={() => setPricingOpen(false)} 
            />
        </div>
    );
}

function mapStatusToStage(status: string, streamStatus: string, activeAgent: string | null, interruptStage: string | undefined): PipelineStage {
    if (streamStatus === 'running') {
        const agent = activeAgent?.toLowerCase() || '';
        if (agent.includes('idea') || agent.includes('research')) return 'research';
        if (agent.includes('hook') || agent.includes('screenplay')) return 'hook';
        if (agent.includes('script') || agent.includes('fact')) return 'script';
        if (agent.includes('edit') || agent.includes('structure') || agent.includes('engagement')) return 'edit';
        
        if (status === 'idea_discovery') return 'research';
        if (status === 'screenplay') return 'hook';
        return 'script';
    }

    if (streamStatus === 'interrupted' && interruptStage) {
        if (interruptStage === 'idea_selection') return 'research';
        if (interruptStage === 'hook_selection') return 'hook';
        if (interruptStage === 'script_edit') return 'script';
        if (interruptStage === 'structure_edit' || interruptStage === 'final_review') return 'edit';
        if (interruptStage === 'strategy_approval') return 'output';
    }
    
    switch (status) {
        case 'idea_discovery':
        case 'researching':
            return 'research';
        case 'screenplay':
            return 'hook';
        case 'editing':
            return 'edit';
        case 'completed':
            return 'output';
        case 'in_progress':
            return 'research';
        default:
            return 'research';
    }
}

function InlineEditTitle({ initialTitle, onSave }: { initialTitle: string, onSave: (val: string) => void }) {
    const [isEditing, setIsEditing] = useState(false);
    const [title, setTitle] = useState(initialTitle);

    if (isEditing) {
        return (
            <input 
                autoFocus
                value={title}
                onChange={e => setTitle(e.target.value)}
                onBlur={() => {
                    setIsEditing(false);
                    if (title.trim()) onSave(title.trim());
                    else setTitle(initialTitle);
                }}
                onKeyDown={e => {
                    if (e.key === 'Enter') {
                        setIsEditing(false);
                        if (title.trim()) onSave(title.trim());
                        else setTitle(initialTitle);
                    }
                    if (e.key === 'Escape') {
                        setIsEditing(false);
                        setTitle(initialTitle);
                    }
                }}
                className="text-sm font-medium bg-surface text-text-primary px-2 py-1 rounded border border-white/10 focus:outline-none focus:border-primary-500"
            />
        );
    }

    return (
        <h1 
            onClick={() => setIsEditing(true)}
            className="text-sm font-medium text-text-primary cursor-pointer hover:text-primary-400 transition-colors border border-transparent hover:border-white/10 px-2 py-1 -ml-2 rounded"
            title="Click to rename"
        >
            {title}
        </h1>
    );
}
