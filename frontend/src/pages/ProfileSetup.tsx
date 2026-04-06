import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { userApi } from '../services/api'
import {
    Sparkles,
    ArrowRight,
    ArrowLeft,
    Loader2,
    Check,
    Youtube,
    Instagram,
    Music2,
    Linkedin,
    Mic2,
    FileText,
    Twitter
} from 'lucide-react'
import { ContentNiche, Platform, ContentStyle, VideoLength, ProfileCreate } from '../types'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const NICHES: ContentNiche[] = [
    'Tech', 'Fitness', 'Finance', 'Education', 'Entertainment',
    'Gaming', 'Lifestyle', 'Travel', 'Food', 'Beauty', 'Other'
]

const PLATFORMS: { value: Platform; label: string; icon: any }[] = [
    { value: 'YouTube', label: 'YouTube', icon: Youtube },
    { value: 'Instagram Reels', label: 'Instagram Reels', icon: Instagram },
    { value: 'TikTok', label: 'TikTok', icon: Music2 },
    { value: 'LinkedIn', label: 'LinkedIn', icon: Linkedin },
    { value: 'Podcast', label: 'Podcast', icon: Mic2 },
    { value: 'Blog', label: 'Blog', icon: FileText },
    { value: 'Twitter/X', label: 'Twitter/X', icon: Twitter },
]

const STYLES: ContentStyle[] = [
    'Educational', 'Entertaining', 'Inspirational', 'Casual',
    'Professional', 'Storytelling', 'Tutorial'
]

const LENGTHS: VideoLength[] = [
    'Short-form (<60s)', 'Medium (1-10 min)', 'Long-form (10+ min)', 'Mixed'
]

export default function ProfileSetup() {
    const navigate = useNavigate()
    const { updateUser } = useAuthStore()
    const [step, setStep] = useState(1)
    const [isLoading, setIsLoading] = useState(false)

    const [formData, setFormData] = useState<ProfileCreate>({
        content_niche: 'Tech',
        custom_niche: '',
        primary_platforms: [],
        content_style: 'Educational',
        target_audience: '',
        typical_video_length: 'Medium (1-10 min)',
        preferred_language: 'English',
        additional_context: ''
    })

    const handleNext = () => {
        if (step === 1 && formData.content_niche === 'Other' && !formData.custom_niche) {
            toast.error('Please specify your niche')
            return
        }
        if (step === 2 && formData.primary_platforms.length === 0) {
            toast.error('Please select at least one platform')
            return
        }
        setStep(step + 1)
    }

    const handleBack = () => {
        setStep(step - 1)
    }

    const handleSubmit = async () => {
        setIsLoading(true)
        try {
            await userApi.createProfile(formData)
            updateUser({ has_profile: true })
            toast.success('Profile created! Let\'s create some content.')
            navigate('/dashboard')
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to create profile')
        } finally {
            setIsLoading(false)
        }
    }

    const handleSkip = () => {
        updateUser({ has_profile: true })
        navigate('/dashboard')
    }

    const togglePlatform = (platform: Platform) => {
        setFormData(prev => ({
            ...prev,
            primary_platforms: prev.primary_platforms.includes(platform)
                ? prev.primary_platforms.filter(p => p !== platform)
                : [...prev.primary_platforms, platform]
        }))
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-surface-50 to-surface-100 dark:from-surface-950 dark:to-surface-900 py-8 px-4">
            {/* Background decoration */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary-500/20 rounded-full blur-3xl" />
                <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-accent-500/20 rounded-full blur-3xl" />
            </div>

            <div className="relative max-w-2xl mx-auto">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 shadow-lg shadow-primary-500/25 mb-4">
                        <Sparkles className="w-6 h-6 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-100">
                        Set up your creator profile
                    </h1>
                    <p className="text-surface-500 dark:text-surface-400 mt-2">
                        Help us personalize your AI-powered content creation experience
                    </p>
                </div>

                {/* Progress */}
                <div className="flex items-center justify-center gap-2 mb-8">
                    {[1, 2, 3, 4].map((s) => (
                        <div
                            key={s}
                            className={clsx(
                                'w-3 h-3 rounded-full transition-all',
                                s === step
                                    ? 'w-8 bg-primary-500'
                                    : s < step
                                        ? 'bg-primary-500'
                                        : 'bg-surface-200 dark:bg-surface-700'
                            )}
                        />
                    ))}
                </div>

                <div className="card p-8">
                    {/* Step 1: Niche */}
                    {step === 1 && (
                        <div className="space-y-6 animate-in">
                            <div>
                                <h2 className="text-xl font-semibold mb-2">What's your content niche?</h2>
                                <p className="text-surface-500 text-sm">Select the category that best describes your content</p>
                            </div>

                            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                                {NICHES.map((niche) => (
                                    <button
                                        key={niche}
                                        onClick={() => setFormData(prev => ({ ...prev, content_niche: niche }))}
                                        className={clsx(
                                            'px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all',
                                            formData.content_niche === niche
                                                ? 'border-primary-500 bg-primary-50 dark:bg-primary-500/20 text-primary-600 dark:text-primary-400'
                                                : 'border-surface-200 dark:border-surface-700 hover:border-surface-300 dark:hover:border-surface-600'
                                        )}
                                        data-testid={`profile-niche-${niche.toLowerCase()}`}
                                    >
                                        {niche}
                                    </button>
                                ))}
                            </div>

                            {formData.content_niche === 'Other' && (
                                <input
                                    type="text"
                                    value={formData.custom_niche}
                                    onChange={(e) => setFormData(prev => ({ ...prev, custom_niche: e.target.value }))}
                                    className="input"
                                    placeholder="Describe your niche..."
                                />
                            )}
                        </div>
                    )}

                    {/* Step 2: Platforms */}
                    {step === 2 && (
                        <div className="space-y-6 animate-in">
                            <div>
                                <h2 className="text-xl font-semibold mb-2">Where do you create content?</h2>
                                <p className="text-surface-500 text-sm">Select all platforms you use</p>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                {PLATFORMS.map(({ value, label, icon: Icon }) => (
                                    <button
                                        key={value}
                                        onClick={() => togglePlatform(value)}
                                        className={clsx(
                                            'flex items-center gap-3 px-4 py-3 rounded-lg border-2 text-left transition-all',
                                            formData.primary_platforms.includes(value)
                                                ? 'border-primary-500 bg-primary-50 dark:bg-primary-500/20'
                                                : 'border-surface-200 dark:border-surface-700 hover:border-surface-300'
                                        )}
                                        data-testid={`profile-platform-${value.toLowerCase().replace(/\s+/g, '-')}`}
                                    >
                                        <Icon className={clsx(
                                            'w-5 h-5',
                                            formData.primary_platforms.includes(value)
                                                ? 'text-primary-500'
                                                : 'text-surface-400'
                                        )} />
                                        <span className="font-medium text-sm">{label}</span>
                                        {formData.primary_platforms.includes(value) && (
                                            <Check className="w-4 h-4 text-primary-500 ml-auto" />
                                        )}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 3: Style & Length */}
                    {step === 3 && (
                        <div className="space-y-6 animate-in">
                            <div>
                                <h2 className="text-xl font-semibold mb-2">What's your content style?</h2>
                                <p className="text-surface-500 text-sm">Choose the tone that matches your content</p>
                            </div>

                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                                {STYLES.map((style) => (
                                    <button
                                        key={style}
                                        onClick={() => setFormData(prev => ({ ...prev, content_style: style }))}
                                        className={clsx(
                                            'px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all',
                                            formData.content_style === style
                                                ? 'border-primary-500 bg-primary-50 dark:bg-primary-500/20 text-primary-600 dark:text-primary-400'
                                                : 'border-surface-200 dark:border-surface-700 hover:border-surface-300'
                                        )}
                                    >
                                        {style}
                                    </button>
                                ))}
                            </div>

                            <div className="pt-4">
                                <h3 className="font-medium mb-3">Typical video length</h3>
                                <div className="grid grid-cols-2 gap-3">
                                    {LENGTHS.map((length) => (
                                        <button
                                            key={length}
                                            onClick={() => setFormData(prev => ({ ...prev, typical_video_length: length }))}
                                            className={clsx(
                                                'px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all',
                                                formData.typical_video_length === length
                                                    ? 'border-accent-500 bg-accent-50 dark:bg-accent-500/20 text-accent-600 dark:text-accent-400'
                                                    : 'border-surface-200 dark:border-surface-700 hover:border-surface-300'
                                            )}
                                        >
                                            {length}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 4: Audience & Context */}
                    {step === 4 && (
                        <div className="space-y-6 animate-in">
                            <div>
                                <h2 className="text-xl font-semibold mb-2">Tell us more about your content</h2>
                                <p className="text-surface-500 text-sm">This helps our AI personalize suggestions</p>
                            </div>

                            <div>
                                <label className="label">Target Audience (optional)</label>
                                <input
                                    type="text"
                                    value={formData.target_audience}
                                    onChange={(e) => setFormData(prev => ({ ...prev, target_audience: e.target.value }))}
                                    className="input"
                                    placeholder="e.g., Young professionals interested in personal finance"
                                />
                            </div>

                            <div>
                                <label className="label">Preferred Language</label>
                                <select
                                    value={formData.preferred_language}
                                    onChange={(e) => setFormData(prev => ({ ...prev, preferred_language: e.target.value }))}
                                    className="input"
                                >
                                    <option value="English">English</option>
                                    <option value="Spanish">Spanish</option>
                                    <option value="French">French</option>
                                    <option value="German">German</option>
                                    <option value="Hindi">Hindi</option>
                                    <option value="Portuguese">Portuguese</option>
                                    <option value="Japanese">Japanese</option>
                                    <option value="Korean">Korean</option>
                                    <option value="Chinese">Chinese</option>
                                </select>
                            </div>

                            <div>
                                <label className="label">Additional Context (optional)</label>
                                <textarea
                                    value={formData.additional_context}
                                    onChange={(e) => setFormData(prev => ({ ...prev, additional_context: e.target.value }))}
                                    className="input min-h-[100px] resize-none"
                                    placeholder="Tell us anything else that would help personalize your content, like your brand voice, specific topics you cover, etc."
                                />
                            </div>
                        </div>
                    )}

                    {/* Navigation */}
                    <div className="flex justify-between mt-8 pt-6 border-t border-surface-200 dark:border-surface-800">
                        {step > 1 ? (
                            <button onClick={handleBack} className="btn-ghost" data-testid="profile-back">
                                <ArrowLeft className="w-4 h-4" />
                                Back
                            </button>
                        ) : (
                            <button onClick={handleSkip} className="btn-ghost text-surface-500" data-testid="profile-skip">
                                Skip for now
                            </button>
                        )}

                        {step < 4 ? (
                            <button onClick={handleNext} className="btn-primary" data-testid="profile-next">
                                Next
                                <ArrowRight className="w-4 h-4" />
                            </button>
                        ) : (
                            <button
                                onClick={handleSubmit}
                                disabled={isLoading}
                                className="btn-accent"
                                data-testid="profile-submit"
                            >
                                {isLoading ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : (
                                    <>
                                        Complete Setup
                                        <Check className="w-4 h-4" />
                                    </>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
