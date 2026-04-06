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
                className: 'dark:bg-surface-800 dark:text-white',
                duration: 4000,
            }}
        />
    </React.StrictMode>,
)
