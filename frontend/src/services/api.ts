import axios from 'axios'
import { User, Profile, Project, ProfileCreate } from '../types'
import { auth } from '../lib/firebase'

export const getBaseUrl = () => {
    let url = (import.meta as any).env?.VITE_API_URL;
    if (url) {
        // Auto-append /api/v1 if the user provided the bare Northflank domain
        if (!url.endsWith('/api/v1')) {
            url = url.replace(/\/$/, '') + '/api/v1';
        }
        return url;
    }
    // Fallback to current browser host to ensure Same-Site cookie compatibility (localhost vs 127.0.0.1)
    const host = typeof window !== 'undefined' ? window.location.hostname : '127.0.0.1';
    return `http://${host}:8000/api/v1`;
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

// Add request interceptor to inject workspace context
api.interceptors.request.use((config) => {
    const workspaceStorage = localStorage.getItem('workspace-storage');
    if (workspaceStorage) {
        try {
            const parsed = JSON.parse(workspaceStorage);
            if (parsed.state?.activeWorkspaceId) {
                config.headers['x-workspace-id'] = parsed.state.activeWorkspaceId;
            }
        } catch (e) {
            // ignore parse error
        }
    }
    return config;
});

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

        // 2. Reactive Firebase token refresh on 401
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true

            // If a refresh is already in flight, wait for it instead of starting a new one
            if (!refreshPromise) {
                refreshPromise = (async () => {
                    const firebaseUser = auth.currentUser;
                    if (!firebaseUser) {
                        throw new Error('No Firebase session');
                    }
                    // Force-refresh the Firebase ID token
                    const newToken = await firebaseUser.getIdToken(true);
                    // Update the backend cookie with the fresh token
                    await axios.post(`${API_URL}/auth/firebase`, { token: newToken }, {
                        withCredentials: true,
                        headers: { 'X-Requested-With': 'XMLHttpRequest' }
                    });
                    return newToken;
                })().finally(() => {
                    refreshPromise = null;
                });
            }

            try {
                await refreshPromise;
                // Retry original request — cookie is now updated
                return api(originalRequest);
            } catch (refreshError) {
                // Refresh failed — clear local state and redirect
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

// Auth API — Firebase-native
export const authApi = {
    firebaseAuth: async (token: string): Promise<User> => {
        const response = await api.post('/auth/firebase', { token })
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
    },

    updateUser: async (data: Partial<User>): Promise<User> => {
        const response = await api.put('/users/me', data)
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

    create: async (title: string, topic: string, project_type: 'series' | 'video' = 'video', requires_continuity: boolean = false): Promise<Project> => {
        const response = await api.post('/projects', { title, topic, project_type, requires_continuity })
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
        onError?: (err: any) => void,
        options: Record<string, any> = {}
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
                niche: options.niche || 'general',
                platforms: options.platforms || ['YouTube'],
                execution_mode: options.execution_mode || 'auto',
                ...options
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
    },

    stop: async (threadId: string) => {
        const response = await api.post(`/pipeline/${threadId}/stop`)
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

// ── Batch 1 Feature APIs ────────────────────────────────────────

// Version History API
export const historyApi = {
    getHistory: async (projectId: string): Promise<any[]> => {
        const response = await api.get(`/projects/${projectId}/history`)
        return response.data
    },

    getVersion: async (projectId: string, versionId: string): Promise<any> => {
        const response = await api.get(`/projects/${projectId}/history/${versionId}`)
        return response.data
    },

    compare: async (projectId: string, v1: string, v2: string): Promise<any> => {
        const response = await api.get(`/projects/${projectId}/history/compare`, {
            params: { v1, v2 }
        })
        return response.data
    },

    restore: async (projectId: string, versionId: string): Promise<any> => {
        const response = await api.post(`/projects/${projectId}/history/${versionId}/restore`)
        return response.data
    },
}

// Voice Profile API
export const voiceApi = {
    analyze: async (scripts: string[]): Promise<any> => {
        const response = await api.post('/voice/analyze', { scripts })
        return response.data
    },

    getProfile: async (): Promise<any> => {
        const response = await api.get('/voice/profile')
        return response.data
    },

    resetProfile: async (): Promise<any> => {
        const response = await api.delete('/voice/profile')
        return response.data
    },
}

// AI Tools API
export const toolsApi = {
    testHook: async (scriptText: string, niche?: string, platform?: string): Promise<any> => {
        const response = await api.post('/tools/hook-test', {
            script_text: scriptText,
            niche: niche || '',
            platform: platform || '',
        })
        return response.data
    },

    generateThumbnailBrief: async (scriptText: string, hookText?: string, topic?: string): Promise<any> => {
        const response = await api.post('/tools/thumbnail-brief', {
            script_text: scriptText,
            hook_text: hookText || '',
            topic: topic || '',
        })
        return response.data
    },

    analyzeCompetitor: async (url: string): Promise<any> => {
        const response = await api.post('/tools/competitor-analysis', { url })
        return response.data
    },
}

// Workspace API
export const workspaceApi = {
    list: async (): Promise<any[]> => {
        const response = await api.get('/workspaces')
        return response.data
    },

    invite: async (workspaceId: string, email: string, role: string): Promise<any> => {
        const response = await api.post(`/workspaces/${workspaceId}/invite`, { email, role })
        return response.data
    },
}

// Billing & Monetization API
export const billingApi = {
    getPackages: async () => {
        const response = await api.get('/billing/packages')
        return response.data
    },

    createOrder: async (packageId: string) => {
        const response = await api.post('/billing/create-order', { package_id: packageId })
        return response.data
    },

    verifyPayment: async (data: { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }) => {
        const response = await api.post('/billing/verify-payment', data)
        return response.data
    },

    getHistory: async () => {
        const response = await api.get('/billing/history')
        return response.data
    },
}

export default api
