import React, { useState, useEffect } from 'react';
import { PackageOpen, Download, CheckCircle, RefreshCw } from 'lucide-react';

export default function Settings() {
  const [deps, setDeps] = useState({ chinese: null, korean: null });
  const [installing, setInstalling] = useState(null);

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
    checkDeps('chinese');
    checkDeps('korean');
  }, []);

  const handleInstall = async (pipeline) => {
    setInstalling(pipeline);
    try {
      await fetch(`http://localhost:8000/api/deps/${pipeline}/install`, { method: 'POST' });
      await checkDeps(pipeline);
    } catch (err) {
      alert("Failed to install dependencies.");
    }
    setInstalling(null);
  };

  const handleUninstall = async (pipeline) => {
    if (!confirm(`Are you sure you want to uninstall the ${pipeline} pipeline dependencies?`)) return;
    try {
      setDeps(prev => ({ ...prev, [pipeline]: null })); // Loading state
      await fetch(`http://localhost:8000/api/deps/${pipeline}/uninstall`, { method: 'POST' });
      await checkDeps(pipeline);
    } catch (err) {
      console.error(err);
      alert("Failed to uninstall.");
    }
  };

  return (
    <div className="animate-fade-in pb-10">
      <h2 className="text-3xl font-bold mb-6 text-white tracking-tight">Settings</h2>
      
      <div className="space-y-6 max-w-4xl">
        <div className="glass-card p-6">
          <h3 className="text-xl font-medium text-white flex items-center gap-2 mb-6">
            <PackageOpen className="text-accent-primary" size={24} /> 
            Pipeline Dependencies
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {['chinese', 'korean'].map(pipeline => (
              <div key={pipeline} className="bg-white/5 border border-white/5 rounded-xl p-5">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h4 className="text-lg font-medium text-gray-200 capitalize">{pipeline} Pipeline</h4>
                    <p className="text-sm text-gray-400 mt-1">
                      {pipeline === 'chinese' ? 'Requires pypinyin' : 'Requires korean-romanizer'}
                    </p>
                  </div>
                  {deps[pipeline]?.ready ? (
                    <div className="flex flex-col items-end gap-2">
                      <span className="flex items-center gap-1 text-accent-success bg-accent-success/10 px-2 py-1 rounded text-xs font-medium">
                        <CheckCircle size={14} /> Installed
                      </span>
                      <button 
                        onClick={() => handleUninstall(pipeline)}
                        className="text-xs px-2 py-1 bg-red-500/10 text-red-400 hover:bg-red-500/20 rounded transition-colors"
                        title="Uninstall Pipeline Dependencies"
                      >
                        🗑️ Uninstall
                      </button>
                    </div>
                  ) : (
                    <span className="flex items-center gap-1 text-accent-warm bg-accent-warm/10 px-2 py-1 rounded text-xs font-medium">
                      Missing
                    </span>
                  )}
                </div>

                {!deps[pipeline]?.ready && deps[pipeline]?.missing && (
                  <div className="mt-4">
                    <ul className="text-sm text-gray-400 mb-4 space-y-2">
                      {deps[pipeline].missing.map((m, i) => (
                        <li key={i} className="flex justify-between items-center bg-black/30 p-2 rounded">
                          <span className="font-mono text-gray-300">{m.pip_name}</span>
                          <span className="text-xs">{m.size}</span>
                        </li>
                      ))}
                    </ul>
                    <button 
                      onClick={() => handleInstall(pipeline)}
                      disabled={installing === pipeline}
                      className="btn-secondary w-full flex items-center justify-center gap-2"
                    >
                      {installing === pipeline ? (
                        <><RefreshCw size={16} className="animate-spin" /> Installing...</>
                      ) : (
                        <><Download size={16} /> Install Dependencies</>
                      )}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
