import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useProjectStore } from '../store/projectStore'
import { useAuthStore } from '../store/authStore'
import {
    Trash2,
    Loader2,
    ArrowRight,
    ChevronRight,
    History
} from 'lucide-react'
import { Project } from '../types'
import toast from 'react-hot-toast'
import { ModeToggle, CreatorMode } from '../components/ui/ModeToggle'
import { PlatformSelector, Platform } from '../components/project/PlatformSelector'
import { MicButton } from '../components/ui/MicButton'

export default function Dashboard() {
    const navigate = useNavigate()
    const { user } = useAuthStore()
    const { projects, isLoading, fetchProjects, createProject, deleteProject } = useProjectStore()
    
    const [topic, setTopic] = useState('')
    const [mode, setMode] = useState<CreatorMode>('auto')
    const [platform, setPlatform] = useState<Platform>('youtube')
    const [isCreating, setIsCreating] = useState(false)
    const [showAllProjects, setShowAllProjects] = useState(false)

    useEffect(() => {
        fetchProjects().catch(() => toast.error('Failed to load projects'))
    }, [])

    const handleCreate = async () => {
        if (!topic.trim()) {
            toast.error('What are we creating today?')
            return
        }

        setIsCreating(true)
        try {
            // Default title from topic
            const title = topic.length > 30 ? topic.substring(0, 27) + '...' : topic
            const project = await createProject(title, topic.trim())
            toast.success('Project initialized')
            navigate(`/project/${project.id}`)
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to initialize project')
        } finally {
            setIsCreating(false)
        }
    }

    const recentProjects = projects.slice(0, 3)

    return (
        <div className="workspace-container max-w-3xl">
            {/* Greeting */}
            <div className="text-center space-y-2 animate-in">
                <h1 className="text-4xl font-display font-bold tracking-tight text-gradient">
                    {getGreeting()}, {user?.display_name?.split(' ')[0] || 'Creator'}
                </h1>
                <p className="text-text-secondary">What's the next big idea?</p>
            </div>

            {/* Central Creation Hub */}
            <div className="space-y-8 animate-in delay-100">
                <div className="relative group">
                    <div className="absolute -inset-1 bg-gradient-to-r from-accent/20 to-accent/0 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500" />
                    <div className="relative flex flex-col gap-4 p-8 bg-surface border border-white/5 rounded-2xl shadow-2xl">
                        <textarea
                            value={topic}
                            onChange={(e) => setTopic(e.target.value)}
                            placeholder="I want to create a video about..."
                            className="w-full bg-transparent text-2xl font-medium placeholder:text-text-secondary/30 border-none focus:ring-0 resize-none min-h-[120px]"
                            data-testid="dashboard-topic-input"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                                    handleCreate()
                                }
                            }}
                        />
                        
                            <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-white/5">
                                <div className="flex items-center gap-4">
                                    <PlatformSelector selected={platform} onChange={setPlatform} />
                                    <div className="h-6 w-[1px] bg-white/5" />
                                    <ModeToggle mode={mode} onChange={setMode} />
                                    <div className="h-6 w-[1px] bg-white/5" />
                                    <MicButton onTranscription={(text) => setTopic(text)} currentText={topic} />
                                </div>

                            <button
                                onClick={handleCreate}
                                disabled={isCreating || !topic.trim()}
                                className="btn-primary px-8 py-3 rounded-xl gap-3 text-lg"
                                data-testid="dashboard-create-project-btn"
                            >
                                {isCreating ? (
                                    <Loader2 className="w-6 h-6 animate-spin" />
                                ) : (
                                    <>
                                        <span>Start Creating</span>
                                        <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                    <div className="absolute bottom-4 right-8 text-[10px] text-text-secondary/50 font-mono">
                        CMD + ENTER TO START
                    </div>
                </div>
            </div>

            {/* Recent / All Projects */}
            <div className="space-y-6 animate-in delay-200">
                <div className="flex items-center justify-between">
                    <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-widest text-text-secondary">
                        <History className="w-4 h-4" />
                        {showAllProjects ? 'All Projects' : 'Recent Work'}
                    </h2>
                    <button 
                        onClick={() => setShowAllProjects(!showAllProjects)}
                        className="text-xs text-accent hover:text-accent-hover transition-colors"
                    >
                        {showAllProjects ? 'Show Less' : 'View Library'}
                    </button>
                </div>

                <div className="grid gap-3" data-testid="dashboard-project-list">
                    {(showAllProjects ? projects : recentProjects).map((project) => (
                        <ProjectRow 
                            key={project.id} 
                            project={project} 
                            onClick={() => navigate(`/project/${project.id}`)}
                            onDelete={async (e) => {
                                e.stopPropagation()
                                if (confirm('Draft will be permanently deleted.')) {
                                    try {
                                        await deleteProject(project.id)
                                        toast.success('Project removed')
                                    } catch {
                                        toast.error('Failed to remove project')
                                    }
                                }
                            }}
                        />
                    ))}
                    
                    {projects.length === 0 && !isLoading && (
                        <div className="p-8 text-center border border-dashed border-white/5 rounded-xl">
                            <p className="text-text-secondary text-sm italic">No history yet. Your creations will appear here.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

function ProjectRow({ project, onClick, onDelete }: { project: Project, onClick: () => void, onDelete: (e: any) => void }) {
    return (
        <div 
            onClick={onClick}
            className="group flex items-center justify-between p-4 bg-surface/50 border border-white/5 rounded-xl hover:bg-elevated hover:border-white/10 transition-all cursor-pointer"
            data-testid={`project-card-${project.id}`}
        >
            <div className="flex items-center gap-4">
                <div className="w-2 h-2 rounded-full bg-accent/50" />
                <div>
                    <h3 className="font-medium text-text-primary group-hover:text-accent transition-colors">{project.title}</h3>
                    <p className="text-xs text-text-secondary line-clamp-1">{project.topic}</p>
                </div>
            </div>
            
            <div className="flex items-center gap-4">
                <span className="text-[10px] font-mono text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity">
                    {new Date(project.created_at).toLocaleDateString()}
                </span>
                <button 
                    onClick={onDelete}
                    className="p-1.5 text-text-secondary hover:text-error transition-colors opacity-0 group-hover:opacity-100"
                >
                    <Trash2 className="w-4 h-4" />
                </button>
                <ChevronRight className="w-4 h-4 text-text-secondary" />
            </div>
        </div>
    )
}

function getGreeting() {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
}

