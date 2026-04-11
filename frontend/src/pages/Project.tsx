import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProjectStore } from '../store/projectStore';
import { useStreamingStore } from '../store/streamingStore';
import { usePipelineStream } from '../hooks/usePipelineStream';
import { 
  ArrowLeft, 
  Sparkles, 
  Loader2, 
  ChevronRight, 
  History,
  Zap,
  Play
} from 'lucide-react';
import toast from 'react-hot-toast';
import { PipelineFlow, PipelineStage } from '../components/pipeline/PipelineFlow';
import { PlatformSelector, Platform } from '../components/project/PlatformSelector';
import { ModeSelector, ExecutionMode } from '../components/project/ModeSelector';
import { OutputEditor } from '../components/project/OutputEditor';
import { MicButton } from '../components/ui/MicButton';

export default function Project() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { currentProject, isLoading, fetchProject } = useProjectStore();
    const { status, streamedContent, threadId } = useStreamingStore();
    const { startPipeline, resumePipeline, checkPipelineStatus } = usePipelineStream();

    const [platform, setPlatform] = useState<Platform>('youtube');
    const [mode, setMode] = useState<ExecutionMode>('auto');
    const [displayContent, setDisplayContent] = useState('');
    const [instruction, setInstruction] = useState('');
    const contentRef = useRef('');

    useEffect(() => {
        if (id) {
            fetchProject(id).catch(() => {
                toast.error('Failed to load project');
                navigate('/dashboard');
            });
            checkPipelineStatus(`${id}:current`).catch(console.error);
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
            setDisplayContent(streamedContent || currentProject?.generated_script || '');
            contentRef.current = streamedContent || currentProject?.generated_script || '';
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

    const currentStage = mapStatusToStage(currentProject.status, status);
    const completedStages = (currentProject.completed_stages || []) as PipelineStage[];

    const handleStart = async () => {
        if (!id) return;
        try {
            await startPipeline(id, currentProject.topic, { 
                platforms: [platform],
                platform: platform,
                execution_mode: mode
            });
            toast.success('Pipeline engaged');
        } catch (err) {
            toast.error('Failed to start pipeline');
        }
    };

    const handleFeedback = async (text?: string) => {
        const feedback = text || instruction;

        if (status === 'idle') {
            await handleStart();
            return;
        }

        if (!feedback.trim() || !threadId) return;

        try {
            await resumePipeline(threadId, 'feedback', currentProject.status, { feedback });
            setInstruction('');
            toast.success('Instruction sent');
        } catch (err) {
            toast.error('Failed to send instruction');
        }
    };

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
                        <h1 className="text-sm font-medium text-text-primary">{currentProject.title}</h1>
                        <ChevronRight className="w-4 h-4 text-text-secondary" />
                        <span className="text-xs text-text-secondary font-mono uppercase tracking-wider">{currentProject.status}</span>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <ModeSelector selected={mode} onChange={setMode} />
                    <div className="h-6 w-[1px] bg-white/10 mx-2" />
                    <PlatformSelector selected={platform} onChange={setPlatform} />
                    <div className="h-6 w-[1px] bg-white/10 mx-2" />
                    <button className="btn-secondary py-1.5 px-3 text-xs gap-2">
                        <History className="w-4 h-4" />
                        Versions
                    </button>
                    {status === 'idle' && (
                        <button 
                            onClick={handleStart} 
                            data-testid="project-execute-btn"
                            className="btn-primary py-1.5 px-4 text-xs gap-2 shadow-glow animate-pulse hover:animate-none"
                        >
                            <Play className="w-3.5 h-3.5 fill-current" />
                            Execute
                        </button>
                    )}
                </div>
            </header>

            {/* Core Pipeline Navigation */}
            <div className="sticky top-16 bg-bg/50 backdrop-blur-sm border-b border-white/5 z-40">
                <PipelineFlow currentStage={currentStage} completedStages={completedStages} />
            </div>

            {/* Main Workspace */}
            <main className="flex-1 workspace-container relative">
                
                {/* Active Stage Overlay */}
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full pointer-events-none overflow-hidden -z-10">
                    <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-accent/5 rounded-full blur-[120px] animate-pulse" />
                </div>

                {/* Content Area */}
                <div className="space-y-12 animate-in slide-up">
                    {/* Research Stage View */}
                    {currentStage === 'research' && (
                        <div className="space-y-8 max-w-4xl mx-auto">
                            <div className="text-center space-y-4">
                                <Zap className="w-8 h-8 text-accent mx-auto" />
                                <h2 className="text-3xl font-display font-bold">Discovery Phase</h2>
                                <p className="text-text-secondary max-w-lg mx-auto">Gathering intelligence and viral signals for your topic.</p>
                            </div>

                            {status === 'running' && !currentProject.discovered_ideas?.length ? (
                                <div className="py-20 flex flex-col items-center gap-4">
                                    <div className="w-12 h-1 bg-white/5 rounded-full overflow-hidden">
                                        <div className="h-full bg-accent animate-[shimmer_2s_infinite]" style={{ width: '40%' }} />
                                    </div>
                                    <p className="text-xs text-text-secondary font-mono animate-pulse uppercase tracking-[0.2em]">Scanning knowledge base...</p>
                                </div>
                            ) : (
                                <div className="grid gap-6 sm:grid-cols-2">
                                    {(currentProject.discovered_ideas || []).map((idea: any, i: number) => (
                                        <div 
                                            key={i} 
                                            className="card-minimal group cursor-pointer border border-transparent hover:border-accent/20"
                                            data-testid={`project-idea-card-${i}`}
                                        >
                                            <h3 className="font-semibold text-lg mb-2 group-hover:text-accent transition-colors">{idea.title}</h3>
                                            <p className="text-sm text-text-secondary line-clamp-3 mb-4">{idea.description}</p>
                                            <div className="flex items-center gap-2">
                                                <span className="badge-minimal border-accent/30 text-accent">9.2 Viral Potential</span>
                                                <span className="text-[10px] text-text-secondary font-mono">{idea.unique_angle}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Scripting Stage View (Streaming) */}
                    {(currentStage === 'script' || currentStage === 'edit') && (
                        <div className="max-w-4xl mx-auto space-y-8">
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

                            <div className="relative p-12 bg-surface/50 border border-white/5 rounded-[2rem] min-h-[600px] shadow-2xl">
                                <div className="prose prose-invert prose-lg max-w-none">
                                    <pre 
                                        className="whitespace-pre-wrap font-sans text-xl leading-relaxed text-text-primary/90"
                                        data-testid="project-script-content"
                                    >
                                        {displayContent}
                                        {status === 'running' && <span className="inline-block w-2 h-6 bg-accent ml-1 animate-pulse" />}
                                    </pre>
                                </div>
                                
                                {!displayContent && status !== 'running' && (
                                    <div className="absolute inset-0 flex flex-col items-center justify-center text-text-secondary/20">
                                        <Zap className="w-12 h-12 mb-4" />
                                        <p className="font-display italic">Awaiting instructions...</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Output Stage View */}
                    {currentStage === 'output' && (
                        <OutputEditor 
                            content={displayContent}
                            hooks={['"Why everything you know about AI is wrong..."', '"Stop scrolling. This script just saved me 10 hours."', '"The hidden truth behind CreatorIQ..."']}
                            strategy="Targeting tech-savvy creators who want to automate their workflow without losing their unique voice."
                        />
                    )}
                </div>
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
                        <button 
                            onClick={() => handleFeedback()}
                            disabled={!instruction.trim() || status === 'running'}
                            className="p-3 bg-accent text-bg rounded-xl hover:bg-accent-hover transition-all disabled:opacity-30"
                        >
                            <Sparkles className="w-5 h-5 fill-current" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

function mapStatusToStage(status: string, streamStatus: string): PipelineStage {
    if (streamStatus === 'running') {
        if (status === 'idea_discovery') return 'research';
        if (status === 'screenplay') return 'hook';
        return 'script';
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
        default:
            return 'research';
    }
}

