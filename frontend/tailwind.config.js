/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // Creative OS Core Palette
                bg: '#0B0B0C',
                surface: '#121214',
                elevated: '#18181B',
                'text-primary': '#EAEAF0',
                'text-secondary': '#9A9AA3',
                
                // Single Accent System (Indigo)
                accent: {
                    DEFAULT: '#6366F1',
                    hover: '#7C7FFF',
                    glow: 'rgba(99, 102, 241, 0.15)',
                },
                
                // Functional States
                success: '#22C55E',
                warning: '#F59E0B',
                error: '#EF4444',

                // Backward compatibility mappings
                primary: {
                    50: '#f0f9ff',
                    100: '#e0f2fe',
                    200: '#bae6fd',
                    300: '#7dd3fc',
                    400: '#38bdf8',
                    500: '#6366F1', // Re-mapped to Indigo
                    600: '#4F46E5',
                    700: '#4338CA',
                    800: '#3730A3',
                    900: '#312E81',
                    950: '#1E1B4B',
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'monospace'],
                display: ['Outfit', 'Inter', 'sans-serif'],
            },
            animation: {
                'fade-in': 'fadeIn 0.3s ease-out',
                'slide-up': 'slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
                'glow': 'glow 2s infinite alternate',
                'shimmer': 'shimmer 2s infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { transform: 'translateY(20px)', opacity: '0' },
                    '100%': { transform: 'translateY(0)', opacity: '1' },
                },
                shimmer: {
                    '0%': { backgroundPosition: '-200% 0' },
                    '100%': { backgroundPosition: '200% 0' },
                },
                glow: {
                    '0%': { boxShadow: '0 0 5px rgba(99, 102, 241, 0.1)' },
                    '100%': { boxShadow: '0 0 20px rgba(99, 102, 241, 0.3)' },
                }
            },
        },

    },
    plugins: [],
}
