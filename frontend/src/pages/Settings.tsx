import { useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { userApi } from '../services/api'
import { Profile } from '../types'
import {
    User,
    Save,
    Loader2,
    Sparkles,
    Shield,
    Globe
} from 'lucide-react'
import toast from 'react-hot-toast'

export default function Settings() {
    const { user } = useAuthStore()
    const [profile, setProfile] = useState<Profile | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)

    useEffect(() => {
        const timeout = setTimeout(() => {
            if (isLoading) {
                console.warn("Settings profile load timed out");
                setIsLoading(false);
            }
        }, 5000); // 5s safety timeout

        loadProfile()
        return () => clearTimeout(timeout)
    }, [])

    const loadProfile = async () => {
        try {
            // Check if user even has a profile indicated
            if (user && !user.has_profile) {
                console.log("User marked as not having profile, skipping load");
                setIsLoading(false);
                return;
            }

            const data = await userApi.getProfile()
            setProfile(data)
        } catch (error: any) {
            console.error("Failed to load profile:", error)
            // If 404, the user might need to setup
            if (error.response?.status === 404) {
                toast.error("Profile not found. Please complete setup.")
            }
        } finally {
            setIsLoading(false)
        }
    }

    const handleSaveProfile = async () => {
        if (!profile) return

        setIsSaving(true)
        try {
            await userApi.updateProfile({
                content_niche: profile.content_niche as any,
                primary_platforms: profile.primary_platforms as any,
                content_style: profile.content_style as any,
                target_audience: profile.target_audience,
                typical_video_length: profile.typical_video_length as any,
                preferred_language: profile.preferred_language,
                additional_context: profile.additional_context
            })
            toast.success('Preferences synchronized')
        } catch (error) {
            toast.error('Failed to save profile')
        } finally {
            setIsSaving(false)
        }
    }

    if (isLoading) {
        return (
            <div className="flex h-[80vh] items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-accent" />
            </div>
        )
    }

    return (
        <div className="max-w-4xl mx-auto px-6 py-12 space-y-16 animate-in slide-up">
            <header className="space-y-4">
                <h1 className="text-4xl font-display font-bold text-gradient">System Configuration</h1>
                <p className="text-text-secondary max-w-xl">
                    Fine-tune your Creative OS environment and AI persona settings.
                </p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
                {/* Sidebar Navigation (Visual Only for now) */}
                <div className="space-y-2">
                    <button className="w-full flex items-center gap-3 px-4 py-2 rounded-lg bg-accent/5 text-accent text-sm font-semibold transition-all">
                        <Sparkles className="w-4 h-4" />
                        AI Persona
                    </button>
                    <button className="w-full flex items-center gap-3 px-4 py-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-white/5 text-sm font-semibold transition-all">
                        <User className="w-4 h-4" />
                        Account
                    </button>
                    <button className="w-full flex items-center gap-3 px-4 py-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-white/5 text-sm font-semibold transition-all">
                        <Shield className="w-4 h-4" />
                        Security
                    </button>
                    <button className="w-full flex items-center gap-3 px-4 py-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-white/5 text-sm font-semibold transition-all">
                        <Globe className="w-4 h-4" />
                        Connections
                    </button>
                </div>

                <div className="md:col-span-2 space-y-12">
                    {/* Account Section */}
                    <section className="space-y-6">
                        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
                            Identity
                        </div>
                        <div className="card-minimal space-y-6">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <label className="text-xs text-text-secondary font-mono">Display Name</label>
                                    <input
                                        type="text"
                                        value={user?.display_name || ''}
                                        className="w-full bg-white/2 border-white/5 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors"
                                        disabled
                                        data-testid="settings-display-name"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs text-text-secondary font-mono">Control Email</label>
                                    <input
                                        type="email"
                                        value={user?.email || ''}
                                        className="w-full bg-white/2 border-white/5 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors"
                                        disabled
                                        data-testid="settings-email"
                                    />
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Creator Profile */}
                    {profile && (
                        <section className="space-y-6">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent">
                                    AI Orchestration
                                </div>
                                <button
                                    onClick={handleSaveProfile}
                                    disabled={isSaving}
                                    className="btn-primary py-1.5 px-4 text-xs gap-2"
                                    data-testid="settings-save-btn"
                                >
                                    {isSaving ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <>
                                            <Save className="w-3.5 h-3.5" />
                                            Update Profile
                                        </>
                                    )}
                                </button>
                            </div>

                            <div className="card-minimal space-y-8">
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
                                    <div className="space-y-2">
                                        <label className="text-xs text-text-secondary font-mono">Domain Niche</label>
                                        <div className="bg-white/2 border border-white/5 rounded-lg px-4 py-2.5 text-sm text-text-primary font-medium">
                                            {profile.content_niche}
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-xs text-text-secondary font-mono">Content Tone</label>
                                        <div className="bg-white/2 border border-white/5 rounded-lg px-4 py-2.5 text-sm text-text-primary font-medium">
                                            {profile.content_style}
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    <label className="text-xs text-text-secondary font-mono">Target Audience Architecture</label>
                                    <input
                                        type="text"
                                        value={profile.target_audience || ''}
                                        onChange={(e) => setProfile({ ...profile, target_audience: e.target.value })}
                                        className="w-full bg-white/2 border-white/5 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors placeholder:text-text-secondary/20"
                                        placeholder="Target demographic, pain points, interests..."
                                        data-testid="settings-audience-input"
                                    />
                                </div>

                                <div className="space-y-3">
                                    <label className="text-xs text-text-secondary font-mono">Style Constraints & Guidance</label>
                                    <textarea
                                        value={profile.additional_context || ''}
                                        onChange={(e) => setProfile({ ...profile, additional_context: e.target.value })}
                                        className="w-full bg-white/2 border-white/5 rounded-lg px-4 py-6 text-sm text-text-primary focus:border-accent/50 transition-colors placeholder:text-text-secondary/20 min-h-[160px] resize-none leading-relaxed"
                                        placeholder="Input specific rules, preferred phrases, or structural requirements for the AI to follow..."
                                        data-testid="settings-context-textarea"
                                    />
                                </div>
                            </div>
                        </section>
                    )}
                </div>
            </div>
        </div>
    )
}
