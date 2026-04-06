import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import {
    Home,
    Settings,
    LogOut,
    Sparkles,
    User,
    ChevronDown
} from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import clsx from 'clsx'

export default function Layout() {
    const { user, logout } = useAuthStore()
    const navigate = useNavigate()
    const location = useLocation()
    const [showUserMenu, setShowUserMenu] = useState(false)
    const menuRef = useRef<HTMLDivElement>(null)

    // Close menu on outside click
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setShowUserMenu(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const handleLogout = async () => {
        await logout()
        navigate('/login')
    }

    const navItems = [
        { path: '/dashboard', label: 'Dashboard', icon: Home },
        { path: '/settings', label: 'Settings', icon: Settings },
    ]

    // Don't show layout on project page since it has its own header
    const isProjectPage = location.pathname.startsWith('/project/')

    if (isProjectPage) {
        return (
            <div className="min-h-screen bg-bg">
                <main>
                    <Outlet />
                </main>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-bg text-text-primary">
            {/* Minimal Header */}
            <header className="sticky top-0 z-50 glass border-b border-white/5">
                <div className="max-w-5xl mx-auto px-6">
                    <div className="flex items-center justify-between h-16">
                        {/* Logo */}
                        <Link to="/dashboard" className="flex items-center gap-3 group">
                            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center shadow-glow">
                                <Sparkles className="w-4 h-4 text-white" />
                            </div>
                            <span className="text-lg font-display font-bold tracking-tight">CreatorIQ</span>
                        </Link>

                        {/* Navigation */}
                        <nav className="flex items-center gap-2">
                            {navItems.map((item) => (
                                <Link
                                    key={item.path}
                                    to={item.path}
                                    className={clsx(
                                        'px-4 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-widest transition-all',
                                        location.pathname === item.path
                                            ? 'text-accent bg-accent/5'
                                            : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
                                    )}
                                >
                                    {item.label}
                                </Link>
                            ))}
                            
                            <div className="h-4 w-[1px] bg-white/10 mx-2" />

                            {/* User menu */}
                            <div className="relative" ref={menuRef}>
                                <button
                                    onClick={() => setShowUserMenu(!showUserMenu)}
                                    className="flex items-center gap-2 pl-2 pr-1 py-1 rounded-lg hover:bg-white/5 transition-colors border border-transparent hover:border-white/5"
                                >
                                    <div className="w-6 h-6 rounded-full bg-accent/20 flex items-center justify-center">
                                        <User className="w-3 h-3 text-accent" />
                                    </div>
                                    <ChevronDown className="w-3 h-3 text-text-secondary" />
                                </button>

                                {showUserMenu && (
                                    <div className="absolute right-0 mt-2 w-48 py-2 bg-elevated border border-white/5 rounded-xl shadow-2xl animate-in slide-up">
                                        <div className="px-4 py-2 border-b border-white/5 mb-1">
                                            <p className="text-xs font-bold text-text-primary truncate">
                                                {user?.display_name}
                                            </p>
                                            <p className="text-[10px] text-text-secondary truncate">{user?.email}</p>
                                        </div>
                                        <Link
                                            to="/settings"
                                            className="flex items-center gap-2 px-4 py-2 text-xs text-text-secondary hover:text-text-primary hover:bg-white/5"
                                            onClick={() => setShowUserMenu(false)}
                                        >
                                            <Settings className="w-3.5 h-3.5" />
                                            Settings
                                        </Link>
                                        <button
                                            onClick={handleLogout}
                                            className="w-full flex items-center gap-2 px-4 py-2 text-xs text-error hover:bg-error/5"
                                        >
                                            <LogOut className="w-3.5 h-3.5" />
                                            Sign out
                                        </button>
                                    </div>
                                )}
                            </div>
                        </nav>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main>
                <Outlet />
            </main>
        </div>
    )
}
