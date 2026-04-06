import { Link } from 'react-router-dom'
import { Sparkles, ArrowRight, Play, Layout, Zap, Bot } from 'lucide-react'

export default function Landing() {
    return (
        <div className="min-h-screen bg-surface-50 dark:bg-surface-950 overflow-hidden selection:bg-primary-500/30">
            {/* Navigation */}
            <nav className="fixed top-0 w-full z-50 bg-white/80 dark:bg-surface-950/80 backdrop-blur-md border-b border-surface-200 dark:border-surface-800 transition-all duration-300">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <div className="flex items-center gap-2">
                            <div className="inline-flex flex-shrink-0 items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 shadow-lg shadow-primary-500/25">
                                <Sparkles className="w-4 h-4 text-white" />
                            </div>
                            <span className="text-xl font-bold gradient-text">CreateIQ</span>
                        </div>
                        <div className="flex items-center gap-4">
                            <Link to="/login" className="text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white font-medium transition-colors">
                                Sign In
                            </Link>
                            <Link to="/signup" className="btn-primary py-2 px-4 shadow-lg shadow-primary-500/25 rounded-full hover:-translate-y-0.5 transition-all">
                                Get Started
                            </Link>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <main className="relative pt-32 pb-16 sm:pt-40 sm:pb-24 lg:pb-32 px-4 flex flex-col items-center flex-grow justify-center min-h-screen z-10">
                {/* Abstract Background Elements */}
                <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
                    <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-primary-500/20 rounded-full blur-[120px] mix-blend-screen opacity-50 animate-pulse"></div>
                    <div className="absolute top-1/3 left-1/4 w-[600px] h-[600px] bg-accent-500/20 rounded-full blur-[100px] mix-blend-screen opacity-40"></div>
                </div>

                <div className="relative text-center max-w-4xl mx-auto z-10 isolate">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-100 dark:bg-surface-800/50 border border-surface-200 dark:border-surface-700 text-sm font-medium text-surface-600 dark:text-surface-300 mb-8 hover:bg-surface-200 dark:hover:bg-surface-800 transition-colors cursor-pointer group backdrop-blur-sm -translate-y-2 opacity-0 animate-[fade-in-down_0.5s_ease-out_forwards]">
                        <span className="flex h-2 w-2 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-500"></span>
                        </span>
                        Introducing CreateIQ V4
                        <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
                    </div>
                    
                    <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-surface-900 dark:text-white mb-8 opacity-0 animate-[fade-in-up_0.5s_ease-out_0.2s_forwards]">
                        AI-Powered Content <br className="hidden sm:block" />
                        <span className="gradient-text bg-clip-text text-transparent bg-gradient-to-r from-primary-400 via-accent-300 to-primary-600 animate-gradient-x">At The Speed Of Thought</span>
                    </h1>
                    
                    <p className="mt-4 max-w-2xl mx-auto text-xl text-surface-600 dark:text-surface-400 mb-10 opacity-0 animate-[fade-in-up_0.5s_ease-out_0.4s_forwards]">
                        Break through creative block instantly. Generate flawless scripts, manage high-performing projects, and discover trending ideas in one unified platform.
                    </p>
                    
                    <div className="flex flex-col sm:flex-row gap-4 justify-center items-center opacity-0 animate-[fade-in-up_0.5s_ease-out_0.6s_forwards]">
                        <Link to="/signup" className="btn-primary px-8 py-4 text-lg rounded-full shadow-xl shadow-primary-500/30 hover:-translate-y-1 hover:shadow-primary-500/40 w-full sm:w-auto flex items-center justify-center gap-2 transition-all">
                            Start creating for free
                            <ArrowRight className="w-5 h-5" />
                        </Link>
                        <a href="#features" className="px-8 py-4 text-lg rounded-full border border-surface-300 dark:border-surface-700 text-surface-700 dark:text-surface-200 hover:bg-surface-50 dark:hover:bg-surface-800 w-full sm:w-auto flex items-center justify-center gap-2 transition-all group backdrop-blur-sm">
                            <Play className="w-5 h-5 group-hover:text-primary-500 transition-colors" />
                            See how it works
                        </a>
                    </div>
                </div>

                {/* Dashboard Preview Mockup */}
                <div className="relative mt-20 max-w-5xl mx-auto w-full px-4 z-10 opacity-0 animate-[fade-in-up_0.8s_ease-out_0.8s_forwards]">
                    <div className="rounded-2xl border border-surface-200 dark:border-surface-800 bg-white/50 dark:bg-surface-900/50 backdrop-blur-xl shadow-2xl p-2 sm:p-4 perspective-1000">
                        <div className="rounded-xl overflow-hidden border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950 aspect-[16/9] relative transform transition-transform hover:scale-[1.01] duration-500 flex items-center justify-center">
                            {/* Simplistic Wireframe of Dashboard */}
                            <div className="absolute inset-x-0 top-0 h-10 border-b border-surface-200 dark:border-surface-800 flex items-center px-4 gap-2">
                                <div className="w-3 h-3 rounded-full bg-red-400"></div>
                                <div className="w-3 h-3 rounded-full bg-amber-400"></div>
                                <div className="w-3 h-3 rounded-full bg-green-400"></div>
                            </div>
                            <div className="w-full h-full pt-10 flex">
                                <div className="w-48 border-r border-surface-200 dark:border-surface-800 hidden sm:block p-4 space-y-4">
                                    <div className="h-4 w-3/4 bg-surface-200 dark:bg-surface-800 rounded animate-pulse"></div>
                                    <div className="h-4 w-1/2 bg-surface-200 dark:bg-surface-800 rounded animate-pulse"></div>
                                    <div className="h-4 w-5/6 bg-surface-200 dark:bg-surface-800 rounded animate-pulse"></div>
                                </div>
                                <div className="flex-1 p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    <div className="h-32 bg-primary-500/10 border border-primary-500/20 rounded-xl relative overflow-hidden group">
                                        <div className="absolute -inset-0 bg-gradient-to-r from-transparent via-primary-500/10 to-transparent transform -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
                                    </div>
                                    <div className="h-32 bg-surface-100 dark:bg-surface-800/50 rounded-xl animate-pulse"></div>
                                    <div className="h-32 bg-surface-100 dark:bg-surface-800/50 rounded-xl animate-pulse hidden md:block"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Features Highlights */}
                <div id="features" className="max-w-7xl mx-auto w-full px-4 mt-32 grid grid-cols-1 md:grid-cols-3 gap-8 pb-20">
                    <div className="card p-6 bg-white/60 dark:bg-surface-900/60 backdrop-blur-md hover:-translate-y-1 transition-transform">
                        <div className="w-12 h-12 bg-primary-500/10 text-primary-500 rounded-xl flex items-center justify-center mb-4">
                            <Bot className="w-6 h-6" />
                        </div>
                        <h3 className="text-xl font-bold text-surface-900 dark:text-white mb-2">Autonomous Agents</h3>
                        <p className="text-surface-600 dark:text-surface-400">Deploy specialized agents that analyze top-performing content and adapt to your unique voice.</p>
                    </div>
                    <div className="card p-6 bg-white/60 dark:bg-surface-900/60 backdrop-blur-md hover:-translate-y-1 transition-transform">
                        <div className="w-12 h-12 bg-accent-500/10 text-accent-500 rounded-xl flex items-center justify-center mb-4">
                            <Zap className="w-6 h-6" />
                        </div>
                        <h3 className="text-xl font-bold text-surface-900 dark:text-white mb-2">Lightning Fast</h3>
                        <p className="text-surface-600 dark:text-surface-400">Generate full-length video scripts and outlines in milliseconds. Iterate rapidly without breaking flow.</p>
                    </div>
                    <div className="card p-6 bg-white/60 dark:bg-surface-900/60 backdrop-blur-md hover:-translate-y-1 transition-transform">
                        <div className="w-12 h-12 bg-emerald-500/10 text-emerald-500 rounded-xl flex items-center justify-center mb-4">
                            <Layout className="w-6 h-6" />
                        </div>
                        <h3 className="text-xl font-bold text-surface-900 dark:text-white mb-2">Beautiful Projects</h3>
                        <p className="text-surface-600 dark:text-surface-400">Organize your creative chaos with an intuitive, clutter-free workspace designed for modern creators.</p>
                    </div>
                </div>
            </main>
            
            {/* Essential UI animations css */}
            <style dangerouslySetInnerHTML={{__html: `
                @keyframes fade-in-up {
                    0% { opacity: 0; transform: translateY(20px); }
                    100% { opacity: 1; transform: translateY(0); }
                }
                @keyframes fade-in-down {
                    0% { opacity: 0; transform: translateY(-20px); }
                    100% { opacity: 1; transform: translateY(0); }
                }
            `}} />
        </div>
    )
}
