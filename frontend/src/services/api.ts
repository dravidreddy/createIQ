import axios from 'axios'
import { User, Profile, Project, ProfileCreate } from '../types'

const getBaseUrl = () => {
    if ((import.meta as any).env?.VITE_API_URL) {
        return (import.meta as any).env.VITE_API_URL
    }
    // Fallback to current browser host to ensure Same-Site cookie compatibility (localhost vs 127.0.0.1)
    const host = typeof window !== 'undefined' ? window.location.hostname : '127.0.0.1'
    return `http://${host}:8000/api/v1`
}

const API_URL = getBaseUrl()

const api = axios.create({
    baseURL: API_URL,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest' // Mandatory CSRF Protection Header
    }
})

// Single-Flight Refresh tracking to prevent concurrent refresh calls
let refreshPromise: Promise<any> | null = null;

// Add response interceptor for token refresh and standardized response unwrapping
api.interceptors.response.use(
    (response) => {
        // If it's a CreatorResponse envelope, unwrap the data
        if (response.data && response.data.status === 'success') {
            return { ...response, data: response.data.data }
        }
        return response
    },
    async (error) => {
        // 1. Handle CreatorResponse error status if present in response.data
        if (error.response?.data?.status === 'error') {
            const serverError = error.response.data.error;
            // Enrich the error object for the frontend to catch
            error.message = serverError.message || error.message;
            error.code = serverError.code || error.code;
            error.details = serverError.details;
        }

        const originalRequest = error.config

        if (error.response?.status === 401 && !originalRequest._retry && originalRequest.url !== '/auth/login' && originalRequest.url !== '/auth/refresh') {
            originalRequest._retry = true

            // If a refresh is already in flight, wait for it instead of starting a new one
            if (!refreshPromise) {
                refreshPromise = axios.post(`${API_URL}/auth/refresh`, {}, { 
                    withCredentials: true,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                }).finally(() => {
                    refreshPromise = null;
                });
            }

            try {
                await refreshPromise;
                // Retry original request automatically with new cookies
                return api(originalRequest);
            } catch (refreshError) {
                // Refresh failed, prevent infinite loops by clearing persist store
                localStorage.removeItem('auth-storage')
                
                // Only redirect if not already on login/signup pages to avoid refresh loops
                const isAuthPage = window.location.pathname === '/login' || window.location.pathname === '/signup'
                if (!isAuthPage) {
                    window.location.href = '/login'
                }
            }
        }

        return Promise.reject(error)
    }
)

// Auth API
export const authApi = {
    login: async (email: string, password: string): Promise<User> => {
        const response = await api.post('/auth/login', { email, password })
        return response.data
    },

    signup: async (email: string, password: string, display_name: string): Promise<User> => {
        const response = await api.post('/auth/signup', { email, password, display_name })
        return response.data
    },

    getMe: async (): Promise<User> => {
        const response = await api.get('/auth/me')
        return response.data
    },

    logout: async (): Promise<void> => {
        await api.post('/auth/logout')
    }
}

// User API
export const userApi = {
    getProfile: async (): Promise<Profile> => {
        const response = await api.get('/users/profile')
        return response.data
    },

    createProfile: async (data: ProfileCreate): Promise<Profile> => {
        const response = await api.post('/users/profile', data)
        return response.data
    },

    updateProfile: async (data: Partial<ProfileCreate>): Promise<Profile> => {
        const response = await api.put('/users/profile', data)
        return response.data
    },

    getUserWithProfile: async (): Promise<{ user: User; profile: Profile }> => {
        const response = await api.get('/users/me')
        return response.data
    }
}

// Project API
export const projectApi = {
    list: async (page = 1, perPage = 10): Promise<{ projects: Project[]; total: number }> => {
        const response = await api.get('/projects', { params: { page, per_page: perPage } })
        return response.data
    },

    get: async (id: string): Promise<Project> => {
        const response = await api.get(`/projects/${id}`)
        return response.data
    },

    create: async (title: string, topic: string): Promise<Project> => {
        const response = await api.post('/projects', { title, topic })
        return response.data
    },

    update: async (id: string, data: Partial<Project>): Promise<Project> => {
        const response = await api.put(`/projects/${id}`, data)
        return response.data
    },

    delete: async (id: string): Promise<void> => {
        await api.delete(`/projects/${id}`)
    },

    selectIdea: async (projectId: string, ideaIndex: number): Promise<Project> => {
        const response = await api.post(`/projects/${projectId}/select-idea`, null, {
            params: { idea_index: ideaIndex }
        })
        return response.data
    }
}

import { fetchEventSource } from '@microsoft/fetch-event-source'

// Agent API (Legacy compatibility)
export const agentApi = {
    // These now map to the new pipeline structure if needed, or remain as legacy
    discoverIdeas: async (projectId: string): Promise<any> => {
        // Migration: Now we prefer the pipeline stream, but keeping for direct calls
        const response = await api.post(`/agents/${projectId}/discover-ideas`)
        return response.data
    },

    getStatus: async (projectId: string): Promise<any> => {
        const response = await api.get(`/agents/${projectId}/status`)
        return response.data
    },
}

// Unified Pipeline API (V4+)
export const pipelineApi = {
    /**
     * Start the LangGraph pipeline with SSE streaming support.
     * Uses POST to allow rich configuration payload.
     */
    start: async (
        projectId: string, 
        topic: string, 
        onEvent: (event: any) => void,
        onError?: (err: any) => void
    ) => {
        const ctrl = new AbortController();
        
        // Strategy: Use HttpOnly cookies by default (withCredentials)
        // Fallback to token query param if needed (can be expanded if frontend tracks tokens)
        await fetchEventSource(`${API_URL}/pipeline/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'include', // Crucial for cookie-based SSE
            body: JSON.stringify({
                project_id: projectId,
                topic: topic,
                niche: 'general',
                platforms: ['YouTube'],
                execution_mode: 'auto'
            }),
            signal: ctrl.signal,
            async onopen(response) {
                if (response.ok && response.headers.get('content-type') === 'text/event-stream') {
                    return; // everything's good
                } else if (response.status >= 400 && response.status < 500 && response.status !== 429) {
                    throw new Error(`Fatal error: ${response.statusText}`);
                }
            },
            onmessage(msg) {
                if (msg.event === 'heartbeat') return;
                try {
                    const data = JSON.parse(msg.data);
                    onEvent({ type: msg.event, ...data });
                } catch (e) {
                    console.error("Failed to parse SSE message", e);
                }
            },
            onclose() {
                // Done
            },
            onerror(err) {
                if (onError) onError(err);
                throw err; // rethrow to stop the loop if needed
            }
        });

        return ctrl;
    },

    resume: async (projectId: string, action: string, stage: string, data?: any) => {
        const response = await api.post(`/pipeline/resume`, {
            project_id: projectId,
            action,
            stage,
            edited_content: data
        })
        return response.data
    }
}

// V3.3 Adaptive Engine API
export const v3Api = {
    // Agent State
    getState: async (projectId: string): Promise<import('../types').AgentStateResponse> => {
        const response = await api.get(`/projects/${projectId}/state`)
        return response.data
    },

    patchState: async (projectId: string, baseVersion: number, patch: Record<string, any>): Promise<import('../types').AgentStateResponse> => {
        const response = await api.patch(`/projects/${projectId}/state`, {
            base_version: baseVersion,
            patch,
        })
        return response.data
    },

    // Pre-flight Simulation
    simulate: async (request: import('../types').JobSimulationRequest): Promise<import('../types').JobSimulationResponse> => {
        const response = await api.post('/jobs/simulate', request)
        return response.data
    },

    // Metrics
    getMetrics: async (): Promise<string> => {
        const response = await api.get('/metrics', { responseType: 'text' })
        return response.data
    },
}

// Config API
export const configApi = {
    getConfig: async (): Promise<{
        config_version: number;
        v3_3_enabled: boolean;
        streaming_batch_threshold: number;
        heartbeat_interval_ms: number;
        interrupt_version: number;
    }> => {
        const response = await api.get('/pipeline/config')
        return response.data
    }
}

export default api
