import { create } from 'zustand'
import { Project, StreamEvent, QualityMode, AgentStateResponse, JobSimulationResponse } from '../types'
import { projectApi, agentApi, v3Api } from '../services/api'

interface ProjectState {
    projects: Project[]
    currentProject: Project | null
    isLoading: boolean
    streamEvents: StreamEvent[]
    isStreaming: boolean

    // V3.3 control knobs
    qualityMode: QualityMode
    variantCnt: number
    budgetCents: number
    agentState: AgentStateResponse | null
    simulation: JobSimulationResponse | null
    isSimulating: boolean

    // Actions
    fetchProjects: () => Promise<void>
    fetchProject: (id: string) => Promise<void>
    createProject: (title: string, topic: string) => Promise<Project>
    deleteProject: (id: string) => Promise<void>
    selectIdea: (projectId: string, ideaIndex: number) => Promise<void>

    // Agent actions
    runIdeaDiscovery: (projectId: string) => Promise<void>
    runScriptGeneration: (projectId: string) => Promise<void>
    runScreenplayAnalysis: (projectId: string) => Promise<void>
    runEditingImprovement: (projectId: string) => Promise<void>
    runFullPipeline: (projectId: string) => Promise<void>

    // V3.3 actions
    setQualityMode: (mode: QualityMode) => void
    setVariantCnt: (count: number) => void
    simulateJob: () => Promise<JobSimulationResponse>
    fetchAgentState: (projectId: string) => Promise<void>

    // Streaming
    addStreamEvent: (event: StreamEvent) => void
    clearStreamEvents: () => void
    setStreaming: (value: boolean) => void
}

export const useProjectStore = create<ProjectState>((set, get) => ({
    projects: [],
    currentProject: null,
    isLoading: false,
    streamEvents: [],
    isStreaming: false,

    // V3.3 defaults
    qualityMode: 'balanced' as QualityMode,
    variantCnt: 2,
    budgetCents: 5,
    agentState: null,
    simulation: null,
    isSimulating: false,

    fetchProjects: async () => {
        set({ isLoading: true })
        try {
            const data = await projectApi.list()
            set({ projects: data.projects, isLoading: false })
        } catch (error) {
            set({ isLoading: false })
            throw error
        }
    },

    fetchProject: async (id: string) => {
        set({ isLoading: true })
        try {
            const project = await projectApi.get(id)
            set({ currentProject: project, isLoading: false })
        } catch (error) {
            set({ isLoading: false })
            throw error
        }
    },

    createProject: async (title: string, topic: string) => {
        const project = await projectApi.create(title, topic)
        set((state) => ({
            projects: [project, ...state.projects],
            currentProject: project
        }))
        return project
    },

    deleteProject: async (id: string) => {
        await projectApi.delete(id)
        set((state) => ({
            projects: state.projects.filter(p => p.id !== id),
            currentProject: state.currentProject?.id === id ? null : state.currentProject
        }))
    },

    selectIdea: async (projectId: string, ideaIndex: number) => {
        const project = await projectApi.selectIdea(projectId, ideaIndex)
        set({ currentProject: project })
    },

    runIdeaDiscovery: async (projectId: string) => {
        set({ isLoading: true })
        try {
            const result = await agentApi.discoverIdeas(projectId)
            set((state) => ({
                currentProject: state.currentProject?.id === projectId 
                    ? { ...state.currentProject, discovered_ideas: result.ideas } 
                    : state.currentProject,
                isLoading: false
            }))
        } catch (error) {
            set({ isLoading: false })
            throw error
        }
    },

    runScriptGeneration: async (projectId: string) => {
        set({ isLoading: true })
        try {
            const result = await agentApi.generateScript(projectId)
            set((state) => ({
                currentProject: state.currentProject?.id === projectId 
                    ? { ...state.currentProject, generated_script: result.script?.full_script || result.script } 
                    : state.currentProject,
                isLoading: false
            }))
        } catch (error) {
            set({ isLoading: false })
            throw error
        }
    },

    runScreenplayAnalysis: async (projectId: string) => {
        set({ isLoading: true })
        try {
            const result = await agentApi.analyzeScreenplay(projectId)
            set((state) => ({
                currentProject: state.currentProject?.id === projectId 
                    ? { ...state.currentProject, screenplay_guidance: result.guidance } 
                    : state.currentProject,
                isLoading: false
            }))
        } catch (error) {
            set({ isLoading: false })
            throw error
        }
    },

    runEditingImprovement: async (projectId: string) => {
        set({ isLoading: true })
        try {
            const result = await agentApi.editScript(projectId)
            set((state) => ({
                currentProject: state.currentProject?.id === projectId 
                    ? { ...state.currentProject, edited_script: result.edited_script } 
                    : state.currentProject,
                isLoading: false
            }))
        } catch (error) {
            set({ isLoading: false })
            throw error
        }
    },

    runFullPipeline: async (projectId: string) => {
        set({ isLoading: true })
        try {
            const state = get()
            const result = await agentApi.runPipeline(projectId, state.qualityMode, state.variantCnt)
            
            if (result.status === 'accepted') {
                // Poll for background job completion
                const interval = setInterval(async () => {
                    try {
                        const statusResult = await agentApi.getStatus(projectId)
                        if (statusResult.status === 'completed' || statusResult.status === 'failed') {
                            clearInterval(interval)
                            await get().fetchProject(projectId)
                            set({ isLoading: false })
                        }
                    } catch (e) {
                        // ignore poll errors
                    }
                }, 3000)
            } else {
                set((state) => ({
                    currentProject: state.currentProject?.id === projectId 
                        ? { 
                            ...state.currentProject, 
                            generated_script: result.original_script,
                            screenplay_guidance: result.screenplay_guidance,
                            edited_script: result.final_script
                        } 
                        : state.currentProject,
                    isLoading: false
                }))
            }
        } catch (error) {
            set({ isLoading: false })
            throw error
        }
    },

    addStreamEvent: (event: StreamEvent) => {
        // Phase 1: Synchronously update state — pure reducer, no async side-effects
        set((state) => {
            let nextProject = state.currentProject;

            // Optimistic Updates — update local state immediately from stream events
            if (nextProject && event.event_type === 'agent_complete' && event.data) {
                try {
                    const dataObj = typeof event.data === 'string'
                        ? JSON.parse(event.data)
                        : event.data;

                    if (event.agent_name === 'idea_discovery' && dataObj.ideas) {
                        nextProject = { ...nextProject, discovered_ideas: dataObj.ideas };
                    } else if (event.agent_name === 'research_script' && dataObj.script) {
                        nextProject = { ...nextProject, generated_script: dataObj.script.full_script || dataObj.script };
                    } else if (event.agent_name === 'screenplay_structure' && dataObj.guidance) {
                        nextProject = { ...nextProject, screenplay_guidance: dataObj.guidance };
                    } else if (event.agent_name === 'editing_improvement' && dataObj.edited_script) {
                        nextProject = { ...nextProject, edited_script: dataObj.edited_script };
                    }
                } catch (e) {
                    // SSE can deliver partial/malformed JSON during streaming — log but don't crash
                    console.warn('[addStreamEvent] Could not parse SSE data payload:', e);
                }
            }

            return {
                streamEvents: [...state.streamEvents, event],
                currentProject: nextProject
            };
        });

        // Phase 2: Handle terminal-event side-effects OUTSIDE set() to avoid race conditions
        // This runs after React has applied the synchronous state update above.
        if (event.event_type === 'done') {
            const projectId = get().currentProject?.id;
            if (projectId) {
                get().fetchProject(projectId).catch((err) => {
                    console.error('[addStreamEvent] Failed to sync project state after stream:', err);
                });
            }
        }
    },

    clearStreamEvents: () => {
        set({ streamEvents: [] })
    },

    setStreaming: (value: boolean) => {
        set({ isStreaming: value })
    },

    // ─── V3.3 Actions ──────────────────────────────────────────

    setQualityMode: (mode: QualityMode) => {
        set({ qualityMode: mode })
    },

    setVariantCnt: (count: number) => {
        set({ variantCnt: Math.max(1, Math.min(count, 10)) })
    },
    simulateJob: async () => {
        const { qualityMode, variantCnt } = get()
        set({ isSimulating: true })
        try {
            const result = await v3Api.simulate({
                quality_mode: qualityMode,
                variant_cnt: variantCnt,
                user_tier: 'pro'
            })
            set({ simulation: result, isSimulating: false })
            return result
        } catch (error) {
            set({ isSimulating: false })
            console.warn('[simulateJob] V3.3 simulation failed:', error)
            throw error
        }
    },

    fetchAgentState: async (projectId: string) => {
        try {
            const state = await v3Api.getState(projectId)
            set({ agentState: state })
        } catch (error) {
            console.warn('[fetchAgentState] V3.3 state fetch failed:', error)
        }
    },
}))
