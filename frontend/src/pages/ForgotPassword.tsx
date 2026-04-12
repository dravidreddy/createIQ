import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, Mail, ArrowRight, Loader2, ArrowLeft } from 'lucide-react'
import { auth } from '../lib/firebase'
import { sendPasswordResetEmail } from 'firebase/auth'
import toast from 'react-hot-toast'

export default function ForgotPassword() {
    const [email, setEmail] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [isSubmitted, setIsSubmitted] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!email) {
            toast.error('Please enter your email')
            return
        }

        setIsLoading(true)
        try {
            await sendPasswordResetEmail(auth, email)
            setIsSubmitted(true)
            toast.success('Password reset email sent!')
        } catch (error: any) {
            console.error("Password reset error:", error)
            toast.error(error.message || 'Failed to send password reset email. Check if the email is correct.')
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-surface-50 to-surface-100 dark:from-surface-950 dark:to-surface-900 px-4">
            {/* Background decoration */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary-500/20 rounded-full blur-3xl" />
                <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-accent-500/20 rounded-full blur-3xl" />
            </div>

            <div className="relative w-full max-w-md">
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 shadow-xl shadow-primary-500/25 mb-4">
                        <Sparkles className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold gradient-text">CreateIQ</h1>
                </div>

                {/* Main Card */}
                <div className="card p-8">
                    {isSubmitted ? (
                        <div className="text-center">
                            <div className="w-16 h-16 bg-success-100 dark:bg-success-900/30 text-success-500 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Mail className="w-8 h-8" />
                            </div>
                            <h2 className="text-2xl font-bold text-surface-900 dark:text-surface-100 mb-2">
                                Check your email
                            </h2>
                            <p className="text-surface-500 dark:text-surface-400 mb-6">
                                We've sent password reset instructions to <strong>{email}</strong>.
                            </p>
                            <Link to="/login" className="btn-primary w-full py-3 inline-flex justify-center">
                                Back to login
                            </Link>
                        </div>
                    ) : (
                        <>
                            <h2 className="text-2xl font-bold text-surface-900 dark:text-surface-100 mb-2">
                                Reset Password
                            </h2>
                            <p className="text-surface-500 dark:text-surface-400 mb-6">
                                Enter your email address and we'll send you a link to reset your password.
                            </p>

                            <form onSubmit={handleSubmit} className="space-y-5">
                                <div>
                                    <label className="label">Email</label>
                                    <div className="relative">
                                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
                                        <input
                                            type="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            className="input pl-10"
                                            placeholder="you@example.com"
                                            autoComplete="email"
                                            autoFocus
                                            required
                                        />
                                    </div>
                                </div>

                                <button
                                    type="submit"
                                    disabled={isLoading}
                                    className="btn-primary w-full py-3"
                                >
                                    {isLoading ? (
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                    ) : (
                                        <>
                                            Send link
                                            <ArrowRight className="w-5 h-5" />
                                        </>
                                    )}
                                </button>
                            </form>
                            
                            <div className="mt-6 text-center">
                                <Link to="/login" className="inline-flex items-center text-primary-500 hover:text-primary-600 font-medium">
                                    <ArrowLeft className="w-4 h-4 mr-1" />
                                    Back to login
                                </Link>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}
