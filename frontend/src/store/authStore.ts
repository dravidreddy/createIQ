import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User } from '../types'
import { authApi } from '../services/api'
import { auth } from '../lib/firebase'
import { 
    signInWithEmailAndPassword, 
    createUserWithEmailAndPassword, 
    GoogleAuthProvider, 
    signInWithPopup, 
    signOut as firebaseSignOut,
    updateProfile
} from 'firebase/auth'

interface AuthState {
    user: User | null
    isAuthenticated: boolean
    isLoading: boolean

    // Actions
    login: (email: string, password: string) => Promise<void>
    signup: (email: string, password: string, displayName: string) => Promise<void>
    loginWithGoogle: () => Promise<void>
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
                    // 1. Firebase Auth
                    const userCredential = await signInWithEmailAndPassword(auth, email, password)
                    const idToken = await userCredential.user.getIdToken()

                    // 2. Pass token to backend to get session cookie & User object
                    const user = await authApi.firebaseAuth(idToken)

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
                    // 1. Firebase Auth Signup
                    const userCredential = await createUserWithEmailAndPassword(auth, email, password)
                    
                    // Add display name to firebase profile
                    await updateProfile(userCredential.user, { displayName })

                    const idToken = await userCredential.user.getIdToken()

                    // 2. Pass to backend to initialize our User document and get session
                    const user = await authApi.firebaseAuth(idToken)
                    
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

            loginWithGoogle: async () => {
                set({ isLoading: true })
                try {
                    const provider = new GoogleAuthProvider()
                    const userCredential = await signInWithPopup(auth, provider)
                    const idToken = await userCredential.user.getIdToken()

                    const user = await authApi.firebaseAuth(idToken)

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
                    // 1. Sign out of Firebase
                    await firebaseSignOut(auth)
                    // 2. Clear backend session cookie
                    await authApi.logout()
                } catch (error) {
                    console.error("Logout API failed", error)
                } finally {
                    set({
                        user: null,
                        isAuthenticated: false
                    })
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

if (typeof window !== 'undefined') {
    window.addEventListener('storage', (event) => {
        if (event.key === 'auth-storage') {
            const newState = JSON.parse(event.newValue || '{}');
            const currentState = useAuthStore.getState();
            
            if (currentState.isAuthenticated && (!newState.state || !newState.state.isAuthenticated)) {
                useAuthStore.setState({ user: null, isAuthenticated: false });
                window.location.href = '/login';
            }
        }
    });
}
