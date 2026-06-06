import React, { useState, useEffect } from 'react';

export default function Dashboard() {
  const [ollamaStatus, setOllamaStatus] = useState(null);
  const [deps, setDeps] = useState({ chinese: null, korean: null });

  const checkDeps = async (pipeline) => {
    try {
      const res = await fetch(`http://localhost:8000/api/deps/${pipeline}`);
      const data = await res.json();
      setDeps(prev => ({ ...prev, [pipeline]: data }));
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetch('http://localhost:8000/api/ollama/status')
      .then(res => res.json())
      .then(data => setOllamaStatus(data.running))
      .catch(() => setOllamaStatus(false));
      
    checkDeps('chinese');
    checkDeps('korean');
  }, []);

  const renderStatus = (pipeline) => {
    const data = deps[pipeline];
    if (!data) return <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gray-500/10 text-gray-400 text-xs font-medium">Loading...</div>;
    if (data.ready) {
      return (
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-success/10 text-accent-success text-xs font-medium">
          <div className="w-2 h-2 rounded-full bg-accent-success"></div> Ready
        </div>
      );
    }
    return (
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-warm/10 text-accent-warm text-xs font-medium">
          <div className="w-2 h-2 rounded-full bg-accent-warm"></div> Missing Dependency
        </div>
    );
  };

  return (
    <div className="animate-fade-in">
      <h2 className="text-3xl font-bold mb-6 text-white tracking-tight">Dashboard</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="glass-card p-6">
          <h3 className="text-lg font-medium text-white mb-2">Japanese Pipeline</h3>
          <p className="text-sm text-gray-400 mb-4">Base translation engine powered by Sugoi v4. No extra dependencies required.</p>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-success/10 text-accent-success text-xs font-medium">
            <div className="w-2 h-2 rounded-full bg-accent-success"></div> Ready
          </div>
        </div>
        
        <div className="glass-card p-6">
          <h3 className="text-lg font-medium text-white mb-2">Chinese Pipeline</h3>
          <p className="text-sm text-gray-400 mb-4">Translates manhua. Uses local Ollama model.</p>
          {renderStatus('chinese')}
        </div>
        
        <div className="glass-card p-6">
          <h3 className="text-lg font-medium text-white mb-2">Korean Pipeline</h3>
          <p className="text-sm text-gray-400 mb-4">Translates manhwa. Uses local Ollama model.</p>
          {renderStatus('korean')}
        </div>
      </div>

      <div className="glass-card p-6 border-l-4 border-l-accent-primary">
        <h3 className="text-lg font-medium text-white mb-2">System Status</h3>
        <div className="flex items-center gap-6 mt-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center">
              <span className="text-xl">🦙</span>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-200">Ollama Engine (Local LLM)</div>
              <div className={`text-xs ${ollamaStatus ? 'text-accent-success' : 'text-accent-warm'}`}>
                {ollamaStatus === null ? 'Checking...' : ollamaStatus ? 'Running and Available' : 'Sleeping (Will auto-start)'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
