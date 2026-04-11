import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { useThemeStore } from './store/themeStore'
import { useEffect } from 'react'
import { ErrorBoundary } from './components/ErrorBoundary'

// Pages
import Landing from './pages/Landing'
import Login from './pages/Login'
import Signup from './pages/Signup'
import ProfileSetup from './pages/ProfileSetup'
import Dashboard from './pages/Dashboard'
import Series from './pages/Series'
import Project from './pages/Project'
import Settings from './pages/Settings'

// Layout
import Layout from './components/layout/Layout'

// Protected route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, user } = useAuthStore()

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />
    }

    // Redirect to profile setup if user hasn't set up profile
    if (user && !user.has_profile) {
        return <Navigate to="/profile-setup" replace />
    }

    return <>{children}</>
}

// Auth route wrapper (redirects to dashboard if already logged in)
function AuthRoute({ children }: { children: React.ReactNode }) {
    const { isAuthenticated } = useAuthStore()

    if (isAuthenticated) {
        return <Navigate to="/dashboard" replace />
    }

    return <>{children}</>
}

function App() {
    const { isDarkMode } = useThemeStore()

    // Apply dark mode class to document
    useEffect(() => {
        if (isDarkMode) {
            document.documentElement.classList.add('dark')
        } else {
            document.documentElement.classList.remove('dark')
        }
    }, [isDarkMode])

    // Check session health and config on mount
    useEffect(() => {
        const authState = useAuthStore.getState()
        if (authState.isAuthenticated) {
            authState.checkAuth()
        }
        
        // Always fetch global config for feature flags
        import('./store/configStore').then(({ useConfigStore }) => {
            useConfigStore.getState().fetchConfig()
        })
    }, [])

    return (
        <ErrorBoundary>
            <BrowserRouter>
                <Routes>
                {/* Auth routes */}
                <Route path="/login" element={
                    <AuthRoute>
                        <Login />
                    </AuthRoute>
                } />
                <Route path="/signup" element={
                    <AuthRoute>
                        <Signup />
                    </AuthRoute>
                } />

                {/* Profile setup (after signup) */}
                <Route path="/profile-setup" element={
                    <ProfileSetup />
                } />

                {/* Protected routes with layout */}
                <Route element={<Layout />}>
                    <Route path="/dashboard" element={
                        <ProtectedRoute>
                            <Dashboard />
                        </ProtectedRoute>
                    } />
                    <Route path="/series/:id" element={
                        <ProtectedRoute>
                            <Series />
                        </ProtectedRoute>
                    } />
                    <Route path="/project/:id" element={
                        <ProtectedRoute>
                            <Project />
                        </ProtectedRoute>
                    } />
                    <Route path="/settings" element={
                        <ProtectedRoute>
                            <Settings />
                        </ProtectedRoute>
                    } />
                </Route>

                {/* Default route */}
                <Route path="/" element={
                    <AuthRoute>
                        <Landing />
                    </AuthRoute>
                } />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </BrowserRouter>
        </ErrorBoundary>
    )
}

export default App
