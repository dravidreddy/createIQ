import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { Toaster } from 'react-hot-toast'

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <App />
        <Toaster
            position="top-right"
            toastOptions={{
                style: {
                    background: '#1e293b', /* slate-800 for dark mode */
                    color: '#f8fafc',      /* slate-50 for high contrast */
                    border: '1px solid rgba(255,255,255,0.1)'
                },
                duration: 4000,
            }}
        />
    </React.StrictMode>,
)
