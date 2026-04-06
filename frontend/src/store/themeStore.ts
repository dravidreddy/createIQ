import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ThemeState {
    isDarkMode: boolean
    toggleTheme: () => void
    setDarkMode: (value: boolean) => void
}

export const useThemeStore = create<ThemeState>()(
    persist(
        (set) => ({
            isDarkMode: true, // Default to dark mode

            toggleTheme: () => {
                set((state) => ({ isDarkMode: !state.isDarkMode }))
            },

            setDarkMode: (value: boolean) => {
                set({ isDarkMode: value })
            }
        }),
        {
            name: 'theme-storage'
        }
    )
)
