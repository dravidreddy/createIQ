import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User } from '../types'
import { authApi } from '../services/api'

interface AuthState {
    user: User | null
    isAuthenticated: boolean
    isLoading: boolean

    // Actions
    login: (email: string, password: string) => Promise<void>
    signup: (email: string, password: string, displayName: string) => Promise<void>
    logout: () => Promise<void>
    checkAuth: () => Promise<void>
    updateUser: (user: Partial<User>) => void
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            user: null,
            isAuthenticated: false,
            isLoading: false,

            login: async (email: string, password: string) => {
                set({ isLoading: true })
                try {
                    const user = await authApi.login(email, password)

                    // Data is now atomic from the login response, no 
                    // extra 'getMe' call required (prevents race condition).
                    set({
                        user,
                        isAuthenticated: true,
                        isLoading: false
                    })
                } catch (error) {
                    set({ isLoading: false })
                    throw error
                }
            },

            signup: async (email: string, password: string, displayName: string) => {
                set({ isLoading: true })
                try {
                    await authApi.signup(email, password, displayName)

                    // Auto-login after signup
                    const user = await authApi.login(email, password)
                    
                    set({
                        user,
                        isAuthenticated: true,
                        isLoading: false
                    })
                } catch (error) {
                    set({ isLoading: false })
                    throw error
                }
            },

            logout: async () => {
                try {
                    await authApi.logout()
                } catch (error) {
                    console.error("Logout API failed", error)
                } finally {
                    set({
                        user: null,
                        isAuthenticated: false
                    })
                    // Clear local storage explicitly just in case
                    localStorage.removeItem('auth-storage')
                }
            },

            checkAuth: async () => {
                try {
                    const user = await authApi.getMe()
                    set({
                        user,
                        isAuthenticated: true
                    })
                } catch (error) {
                    // Token invalid/missing, clear auth state
                    set({
                        user: null,
                        isAuthenticated: false
                    })
                }
            },

            updateUser: (userData: Partial<User>) => {
                const currentUser = get().user
                if (currentUser) {
                    set({ user: { ...currentUser, ...userData } })
                }
            }
        }),
        {
            name: 'auth-storage',
            partialize: (state) => ({
                user: state.user,
                isAuthenticated: state.isAuthenticated
            })
        }
    )
)

// Handle Multi-Tab Logout / State Synchronization
if (typeof window !== 'undefined') {
    window.addEventListener('storage', (event) => {
        if (event.key === 'auth-storage') {
            const newState = JSON.parse(event.newValue || '{}');
            const currentState = useAuthStore.getState();
            
            // If another tab logged out (isAuthenticated changed from true to false)
            if (currentState.isAuthenticated && (!newState.state || !newState.state.isAuthenticated)) {
                // Perform local cleanup and redirect
                useAuthStore.setState({ user: null, isAuthenticated: false });
                window.location.href = '/login';
            }
        }
    });
}
