import React, { useState, useEffect } from 'react'
import { LayoutDashboard, Languages, Settings as SettingsIcon, Loader2 } from 'lucide-react'

import Dashboard from './views/Dashboard'
import Translate from './views/Translate'
import Settings from './views/Settings'
import Execution from './views/Execution'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isInitializing, setIsInitializing] = useState(true);
  const [isTranslating, setIsTranslating] = useState(false);

  useEffect(() => {
    // Check if the backend is ready and if a translation is actively running
    fetch('http://localhost:8000/api/translate/status')
      .then(res => res.json())
      .then(data => {
        if (data.is_translating) {
          setIsTranslating(true);
          setActiveTab('translate');
        }
        // Artificial delay for smooth UX
        setTimeout(() => setIsInitializing(false), 800);
      })
      .catch(() => {
        // If it fails to connect, just hide the splash screen after 2s
        setTimeout(() => setIsInitializing(false), 2000);
      });
  }, []);

  if (isInitializing) {
    return (
      <div className="flex flex-col items-center justify-center h-screen w-full bg-bg-deep text-white">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-primary to-accent-secondary flex items-center justify-center shadow-[0_0_30px_rgba(59,130,246,0.6)] animate-pulse mb-6">
          <Languages size={32} />
        </div>
        <h1 className="text-3xl font-bold mb-4 tracking-tight">MangaLens</h1>
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 size={18} className="animate-spin" />
          <span className="font-medium text-sm tracking-widest uppercase">Connecting to Core...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full bg-bg-deep overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 glass-panel !rounded-none !border-y-0 !border-l-0 flex flex-col z-10 relative">
        <div className="p-6 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-primary to-accent-secondary flex items-center justify-center shadow-[0_0_15px_rgba(59,130,246,0.5)]">
            <Languages className="text-white" size={24} />
          </div>
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
            MangaLens
          </h1>
        </div>
        
        <nav className="flex-1 px-4 py-6 space-y-2">
          <div 
            onClick={() => setActiveTab('dashboard')} 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
          >
            <LayoutDashboard size={20} /> Dashboard
          </div>
          <div 
            onClick={() => setActiveTab('translate')} 
            className={`nav-item ${activeTab === 'translate' ? 'active' : ''}`}
          >
            <Languages size={20} /> Translate
          </div>
          <div 
            onClick={() => setActiveTab('settings')} 
            className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
          >
            <SettingsIcon size={20} /> Settings
          </div>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden relative">
        <div className="absolute inset-0 p-8 overflow-y-auto">
          {activeTab === 'dashboard' && <Dashboard />}
          {activeTab === 'translate' && <Translate onStart={() => setActiveTab('execution')} />}
          {activeTab === 'execution' && <Execution onComplete={() => setActiveTab('translate')} />}
          {activeTab === 'settings' && <Settings />}
        </div>
      </main>
    </div>
  )
}

export default App
