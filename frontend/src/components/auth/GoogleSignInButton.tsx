import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

interface Props {
  text?: string;
  onSuccess?: () => void;
}

export function GoogleSignInButton({ text = "Continue with Google", onSuccess }: Props) {
    const { loginWithGoogle } = useAuthStore()
    const [isLoading, setIsLoading] = useState(false)
    const navigate = useNavigate()

    const handleGoogleLogin = async () => {
        setIsLoading(true)
        try {
            await loginWithGoogle()
            toast.success('Successfully signed in with Google!')
            if (onSuccess) {
                onSuccess()
            } else {
                navigate('/dashboard')
            }
        } catch (error: any) {
            console.error(error)
            if (error.code === 'auth/popup-closed-by-user') {
                toast.error('Sign-in popup was closed.')
            } else {
                toast.error(error.message || 'Failed to sign in with Google')
            }
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 border border-white/10 rounded-xl bg-elevated text-text-primary hover:bg-white/10 transition-colors font-medium"
        >
            {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M22.56 12.25C22.56 11.47 22.49 10.72 22.36 10H12V14.26H17.92C17.66 15.63 16.89 16.81 15.75 17.58V20.34H19.32C21.41 18.42 22.56 15.6 22.56 12.25Z" fill="#4285F4"/>
                    <path d="M12 23C14.97 23 17.46 22.02 19.32 20.34L15.75 17.58C14.74 18.26 13.48 18.66 12 18.66C9.13999 18.66 6.70999 16.73 5.83999 14.15H2.15999V16.99C3.96999 20.61 7.71 23 12 23Z" fill="#34A853"/>
                    <path d="M5.84 14.15C5.62 13.48 5.49 12.76 5.49 12C5.49 11.24 5.62 10.52 5.84 9.85V7.01H2.16C1.42 8.49 1 10.19 1 12C1 13.81 1.42 15.51 2.16 16.99L5.84 14.15Z" fill="#FBBC05"/>
                    <path d="M12 5.34C13.62 5.34 15.06 5.9 16.2 6.99L19.4 3.79C17.45 1.97 14.96 1 12 1C7.71 1 3.97 3.39 2.16 7.01L5.84 9.85C6.71 7.27 9.14 5.34 12 5.34Z" fill="#EA4335"/>
                </svg>
            )}
            {text}
        </button>
    )
}
