import { useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { userApi, authApi } from '../services/api'
import { Profile } from '../types'
import { User, Save, Loader2, Sparkles, Shield, Globe } from 'lucide-react'
import toast from 'react-hot-toast'

const NICHES = ['Tech', 'Fitness', 'Finance', 'Education', 'Entertainment', 'Gaming', 'Lifestyle', 'Travel', 'Food', 'Beauty', 'Other']
const STYLES = ['Educational', 'Entertaining', 'Inspirational', 'Casual', 'Professional', 'Storytelling', 'Tutorial']
const HOOK_FRAMEWORKS = ['Problem-Agitate-Solve', 'Bold Claim + Proof', 'Question -> Story -> Lesson', 'Status Quo Interruption']
const FORMALITY = ['Highly Casual', 'Neutral', 'Professional Academic']
const PACING = ['Fast/High-Retention (MrBeast style)', 'Conversational/Relaxed', 'Educational/Step-by-Step']

export default function Settings() {
    const { user, updateUser: updateAuthUser } = useAuthStore()
    const [profile, setProfile] = useState<Profile | null>(null)
    const [displayName, setDisplayName] = useState(user?.display_name || '')
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [isSavingUser, setIsSavingUser] = useState(false)
    const [activeTab, setActiveTab] = useState<'persona' | 'account' | 'security' | 'connections'>('persona')

    const [currentPassword, setCurrentPassword] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [isChangingPassword, setIsChangingPassword] = useState(false)

    useEffect(() => {
        if (user) {
            setDisplayName(user.display_name)
        }
        
        const timeout = setTimeout(() => {
            if (isLoading) {
                console.warn("Settings profile load timed out");
                setIsLoading(false);
            }
        }, 5000);

        loadProfile()
        return () => clearTimeout(timeout)
    }, [user])

    const loadProfile = async () => {
        try {
            if (user && !user.has_profile) {
                console.log("User marked as not having profile, skipping load");
                setIsLoading(false);
                return;
            }

            const data = await userApi.getProfile()
            setProfile(data)
        } catch (error: any) {
            console.error("Failed to load profile:", error)
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
                additional_context: profile.additional_context,
                vocabulary: profile.vocabulary,
                avoid_words: profile.avoid_words,
                formality_level: profile.formality_level,
                hook_framework: profile.hook_framework,
                default_cta: profile.default_cta,
                pacing_style: profile.pacing_style,
            })
            toast.success('AI Persona synchronized')
        } catch (error) {
            toast.error('Failed to save persona profile')
        } finally {
            setIsSaving(false)
        }
    }

    const handleSaveAccount = async () => {
        setIsSavingUser(true)
        try {
            const updatedUser = await userApi.updateUser({ display_name: displayName })
            updateAuthUser({ display_name: updatedUser.display_name })
            toast.success('Account Identity updated')
        } catch (error) {
            toast.error('Failed to update account identity')
        } finally {
            setIsSavingUser(false)
        }
    }

    const handleChangePassword = async (e: React.FormEvent) => {
        e.preventDefault()
        if (newPassword !== confirmPassword) {
            toast.error('New passwords do not match')
            return
        }
        if (newPassword.length < 8) {
            toast.error('New password must be at least 8 characters')
            return
        }
        setIsChangingPassword(true)
        try {
            await authApi.changePassword(currentPassword, newPassword)
            toast.success('Password updated successfully')
            setCurrentPassword('')
            setNewPassword('')
            setConfirmPassword('')
        } catch (error: any) {
            toast.error(error.message || 'Failed to update password')
        } finally {
            setIsChangingPassword(false)
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
                <div className="space-y-2">
                    <button 
                        onClick={() => setActiveTab('persona')}
                        className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activeTab === 'persona' ? 'bg-accent/5 text-accent' : 'text-text-secondary hover:text-text-primary hover:bg-white/5'}`}>
                        <Sparkles className="w-4 h-4" />
                        AI Persona
                    </button>
                    <button 
                        onClick={() => setActiveTab('account')}
                        className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activeTab === 'account' ? 'bg-accent/5 text-accent' : 'text-text-secondary hover:text-text-primary hover:bg-white/5'}`}>
                        <User className="w-4 h-4" />
                        Account
                    </button>
                    <button 
                        onClick={() => setActiveTab('security')}
                        className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activeTab === 'security' ? 'bg-accent/5 text-accent' : 'text-text-secondary hover:text-text-primary hover:bg-white/5'}`}>
                        <Shield className="w-4 h-4" />
                        Security
                    </button>
                    <button 
                        onClick={() => setActiveTab('connections')}
                        className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activeTab === 'connections' ? 'bg-accent/5 text-accent' : 'text-text-secondary hover:text-text-primary hover:bg-white/5'}`}>
                        <Globe className="w-4 h-4" />
                        Connections
                    </button>
                </div>

                <div className="md:col-span-2 space-y-12">
                    {/* Account Section */}
                    {activeTab === 'account' && (
                    <section className="space-y-6 animate-fade-in">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
                                Identity
                            </div>
                            <button
                                onClick={handleSaveAccount}
                                disabled={isSavingUser || displayName === user?.display_name}
                                className="btn-primary py-1.5 px-4 text-xs gap-2"
                                data-testid="settings-save-account-btn"
                            >
                                {isSavingUser ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <>
                                        <Save className="w-3.5 h-3.5" />
                                        Save Changes
                                    </>
                                )}
                            </button>
                        </div>
                        <div className="card-minimal space-y-6">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <label className="text-xs text-text-secondary font-mono">Display Name</label>
                                    <input
                                        type="text"
                                        value={displayName}
                                        onChange={(e) => setDisplayName(e.target.value)}
                                        className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors"
                                        placeholder="Creator Name"
                                        data-testid="settings-display-name"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs text-text-secondary font-mono">Control Email</label>
                                    <input
                                        type="email"
                                        value={user?.email || ''}
                                        className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors opacity-50 cursor-not-allowed"
                                        disabled
                                        data-testid="settings-email"
                                    />
                                </div>
                            </div>
                        </div>
                    </section>
                    )}

                    {/* Creator Profile */}
                    {activeTab === 'persona' && profile && (
                        <section className="space-y-6 animate-fade-in">
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
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <label className="text-xs text-text-secondary font-mono">Domain Niche</label>
                                        <select
                                            value={profile.content_niche || ''}
                                            onChange={(e) => setProfile({ ...profile, content_niche: e.target.value })}
                                            className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors"
                                        >
                                            {NICHES.map((niche) => <option className="bg-gray-900 text-white" key={niche} value={niche}>{niche}</option>)}
                                        </select>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-xs text-text-secondary font-mono">Content Tone</label>
                                        <select
                                            value={profile.content_style || ''}
                                            onChange={(e) => setProfile({ ...profile, content_style: e.target.value })}
                                            className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors"
                                        >
                                            {STYLES.map((style) => <option className="bg-gray-900 text-white" key={style} value={style}>{style}</option>)}
                                        </select>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-xs text-text-secondary font-mono">Formality Level</label>
                                        <select
                                            value={profile.formality_level || ''}
                                            onChange={(e) => setProfile({ ...profile, formality_level: e.target.value })}
                                            className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors"
                                        >
                                            <option className="bg-gray-900 text-white" value="">Default (Derived from Tone)</option>
                                            {FORMALITY.map((opt) => <option className="bg-gray-900 text-white" key={opt} value={opt}>{opt}</option>)}
                                        </select>
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    <label className="text-xs text-text-secondary font-mono">Target Audience Architecture</label>
                                    <input
                                        type="text"
                                        value={profile.target_audience || ''}
                                        onChange={(e) => setProfile({ ...profile, target_audience: e.target.value })}
                                        className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors placeholder:text-text-secondary/20"
                                        placeholder="Target demographic, pain points, interests..."
                                    />
                                </div>

                                <hr className="border-white/5" />

                                <div className="space-y-6">
                                    <h4 className="text-sm font-semibold text-text-primary">Content Constraints (Brand Voice)</h4>
                                    <div className="space-y-4">
                                        <div className="space-y-2">
                                            <label className="text-xs text-text-secondary font-mono">Signature Vocabulary (Comma Separated)</label>
                                            <input
                                                type="text"
                                                value={profile.vocabulary || ''}
                                                onChange={(e) => setProfile({ ...profile, vocabulary: e.target.value })}
                                                className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors placeholder:text-text-secondary/20"
                                                placeholder="e.g. Level up, Creator economy, Let's dive in"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs text-text-secondary font-mono">Negative Constraints (Words to Avoid)</label>
                                            <input
                                                type="text"
                                                value={profile.avoid_words || ''}
                                                onChange={(e) => setProfile({ ...profile, avoid_words: e.target.value })}
                                                className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors placeholder:text-text-secondary/20"
                                                placeholder="e.g. Delve, In today's fast-paced world, Furthermore"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <hr className="border-white/5" />

                                <div className="space-y-6">
                                    <h4 className="text-sm font-semibold text-text-primary">Strategic Frameworks</h4>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                        <div className="space-y-2">
                                            <label className="text-xs text-text-secondary font-mono">Hook Framework</label>
                                            <select
                                                value={profile.hook_framework || ''}
                                                onChange={(e) => setProfile({ ...profile, hook_framework: e.target.value })}
                                                className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors"
                                            >
                                                <option className="bg-gray-900 text-white" value="">AI Automated</option>
                                                {HOOK_FRAMEWORKS.map((opt) => <option className="bg-gray-900 text-white" key={opt} value={opt}>{opt}</option>)}
                                            </select>
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs text-text-secondary font-mono">Pacing Style</label>
                                            <select
                                                value={profile.pacing_style || ''}
                                                onChange={(e) => setProfile({ ...profile, pacing_style: e.target.value })}
                                                className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors"
                                            >
                                                <option className="bg-gray-900 text-white" value="">Standard Pacing</option>
                                                {PACING.map((opt) => <option className="bg-gray-900 text-white" key={opt} value={opt}>{opt}</option>)}
                                            </select>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-xs text-text-secondary font-mono">Default Call-To-Action (CTA)</label>
                                        <input
                                            type="text"
                                            value={profile.default_cta || ''}
                                            onChange={(e) => setProfile({ ...profile, default_cta: e.target.value })}
                                            className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors placeholder:text-text-secondary/20"
                                            placeholder="e.g. Subscribe to my newsletter in the description"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    <label className="text-xs text-text-secondary font-mono">Additional Context & Rule Prompts</label>
                                    <textarea
                                        value={profile.additional_context || ''}
                                        onChange={(e) => setProfile({ ...profile, additional_context: e.target.value })}
                                        className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-6 text-sm text-text-primary focus:border-accent/50 transition-colors placeholder:text-text-secondary/20 min-h-[160px] resize-none leading-relaxed"
                                        placeholder="Input specific rules, tone directions, or structural requirements for the AI to follow..."
                                    />
                                </div>
                            </div>
                        </section>
                    )}

                    {/* Security Section */}
                    {activeTab === 'security' && (
                        <section className="space-y-6 animate-fade-in">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
                                    Security Settings
                                </div>
                            </div>
                            <div className="card-minimal space-y-6">
                                <form onSubmit={handleChangePassword} className="space-y-4">
                                    <h4 className="text-sm font-semibold text-text-primary">Change Password</h4>
                                    <div className="space-y-4">
                                        <div className="space-y-2">
                                            <label className="text-xs text-text-secondary font-mono">Current Password</label>
                                            <input
                                                type="password"
                                                required
                                                value={currentPassword}
                                                onChange={(e) => setCurrentPassword(e.target.value)}
                                                className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors placeholder:text-text-secondary/20"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs text-text-secondary font-mono">New Password</label>
                                            <input
                                                type="password"
                                                required
                                                minLength={8}
                                                value={newPassword}
                                                onChange={(e) => setNewPassword(e.target.value)}
                                                className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors placeholder:text-text-secondary/20"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs text-text-secondary font-mono">Confirm New Password</label>
                                            <input
                                                type="password"
                                                required
                                                minLength={8}
                                                value={confirmPassword}
                                                onChange={(e) => setConfirmPassword(e.target.value)}
                                                className="w-full bg-white/5 border-white/10 rounded-lg px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 transition-colors placeholder:text-text-secondary/20"
                                            />
                                        </div>
                                        <button
                                            type="submit"
                                            disabled={isChangingPassword || !currentPassword || !newPassword || !confirmPassword}
                                            className="btn-primary py-2 px-4 w-full text-sm gap-2 mt-2"
                                            data-testid="settings-change-password-btn"
                                        >
                                            {isChangingPassword ? (
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                            ) : (
                                                <>
                                                    <Shield className="w-4 h-4" />
                                                    Change Password
                                                </>
                                            )}
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </section>
                    )}

                    {/* Placeholder Views for uncompleted tabs */}
                    {activeTab === 'connections' && (
                        <section className="flex flex-col items-center justify-center p-12 card-minimal text-center animate-fade-in">
                            <Globe className="w-12 h-12 text-white/10 mb-4" />
                            <h3 className="text-lg font-medium text-text-primary mb-2">Coming Soon</h3>
                            <p className="text-sm text-text-secondary max-w-sm">
                                This configuration matrix is currently locked in your Alpha instance.
                            </p>
                        </section>
                    )}
                </div>
            </div>
        </div>
    )
}
