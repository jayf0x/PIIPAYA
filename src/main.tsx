import React from 'react'
import ReactDOM from 'react-dom/client'
import { Background } from './components/Background'
import { Home } from './Home'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <div className="min-h-screen w-full text-foreground">
      <Background />
      <main className="relative z-10">
        <Home />
      </main>
    </div>
  </React.StrictMode>
)
