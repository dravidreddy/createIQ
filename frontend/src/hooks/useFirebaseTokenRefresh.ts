/**
 * useFirebaseTokenRefresh — Hybrid Token Refresh Strategy
 *
 * Proactively refreshes the Firebase session cookie every 50 minutes
 * (Firebase tokens expire at 60 min). Also refreshes on tab visibility
 * change if the token is likely stale.
 *
 * The reactive 401 interceptor in api.ts serves as the safety net.
 * This hook provides the proactive layer for zero-interruption UX.
 */

import { useEffect, useRef } from 'react'
import { auth } from '../lib/firebase'
import { authApi } from '../services/api'
import { useAuthStore } from '../store/authStore'

// Refresh 10 minutes before expiry (Firebase tokens live 60 min)
const REFRESH_INTERVAL_MS = 50 * 60 * 1000 // 50 minutes
const STALE_THRESHOLD_MS = 45 * 60 * 1000  // Consider stale after 45 min

export function useFirebaseTokenRefresh() {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
    const lastRefreshRef = useRef<number>(Date.now())
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

    useEffect(() => {
        if (!isAuthenticated) {
            // Not logged in — clear any existing timer
            if (timerRef.current) {
                clearInterval(timerRef.current)
                timerRef.current = null
            }
            return
        }

        const refreshCookie = async () => {
            try {
                const firebaseUser = auth.currentUser
                if (!firebaseUser) return

                // Force-refresh the Firebase ID token
                const newToken = await firebaseUser.getIdToken(true)

                // Update the backend cookie with the fresh token
                await authApi.firebaseAuth(newToken)

                lastRefreshRef.current = Date.now()
                console.debug('[TokenRefresh] Cookie refreshed proactively')
            } catch (err) {
                console.warn('[TokenRefresh] Proactive refresh failed:', err)
                // Don't crash — the reactive 401 interceptor will handle it
            }
        }

        // Start the proactive timer
        lastRefreshRef.current = Date.now()
        timerRef.current = setInterval(refreshCookie, REFRESH_INTERVAL_MS)

        // Visibility change handler — refresh if returning to tab after being away
        const handleVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
                const elapsed = Date.now() - lastRefreshRef.current
                if (elapsed > STALE_THRESHOLD_MS) {
                    console.debug('[TokenRefresh] Tab returned after', Math.round(elapsed / 60000), 'min — refreshing')
                    refreshCookie()
                }
            }
        }

        document.addEventListener('visibilitychange', handleVisibilityChange)

        return () => {
            if (timerRef.current) {
                clearInterval(timerRef.current)
                timerRef.current = null
            }
            document.removeEventListener('visibilitychange', handleVisibilityChange)
        }
    }, [isAuthenticated])
}
