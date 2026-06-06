import React, { useState, useEffect } from 'react';
import { Loader2, Activity, Image as ImageIcon, CheckCircle } from 'lucide-react';

export default function Execution({ onComplete }) {
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState([]);
  const [currentImage, setCurrentImage] = useState(null);
  const [translatedKey, setTranslatedKey] = useState(Date.now());

  // SSE Stream
  useEffect(() => {
    setLogs(["🚀 Connecting to log stream..."]);
    const eventSource = new EventSource("http://localhost:8000/api/translate/progress");
    
    eventSource.onmessage = (event) => {
      const data = event.data;
      if (data && data !== "ping") {
        // Parse progress
        const progressMatch = data.match(/\[(\d+)\/(\d+)\]/);
        if (progressMatch) {
          const current = parseInt(progressMatch[1]);
          const total = parseInt(progressMatch[2]);
          setProgress((current / total) * 100);
        }
        
        // Parse current image
        const processingMatch = data.match(/Processing:\s+(.+)/i);
        if (processingMatch) {
          setCurrentImage(processingMatch[1].trim());
        }

        // Parse completion
        if (data.includes("Translation Job Finished") || data.includes("Pipeline Error")) {
          // Add a short delay before returning so user sees 100%
          setTimeout(() => {
            if (onComplete) onComplete();
          }, 3000);
        }
        
        setLogs(prev => {
          const newLogs = [...prev, data];
          if (newLogs.length > 50) return newLogs.slice(newLogs.length - 50);
          return newLogs;
        });
      }
    };
    
    return () => eventSource.close();
  }, [onComplete]);

  // Polling for translated image refresh
  useEffect(() => {
    if (progress > 0 && currentImage) {
      const interval = setInterval(() => {
        setTranslatedKey(Date.now());
      }, 1500);
      return () => clearInterval(interval);
    }
  }, [progress, currentImage]);

  const handleStop = async () => {
    try {
      await fetch('http://localhost:8000/api/translate/stop', { method: 'POST' });
      if (onComplete) onComplete();
    } catch (err) {
      console.error(err);
    }
  };

  const isDetecting = progress === 0 && !currentImage;

  return (
    <div className="animate-fade-in flex flex-col h-full overflow-hidden">
      {/* HEADER */}
      <div className="flex items-center justify-between mb-6 flex-shrink-0">
        <div>
          <h2 className="text-3xl font-bold text-white tracking-tight">
            {isDetecting ? "Language Detection" : "Live Translation"}
          </h2>
          <p className="text-gray-400 mt-1">
            {isDetecting ? "Analyzing first 5 images for language shootout..." : `Processing: ${currentImage || '...'}`}
          </p>
        </div>
        <div className="flex items-center gap-3 bg-black/40 px-4 py-2 rounded-xl border border-white/5">
          <Activity className="text-accent-primary animate-pulse" />
          <span className="text-white font-mono">{Math.round(progress)}%</span>
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex gap-6 overflow-hidden min-h-0 mb-6">
        
        {isDetecting ? (
          // PHASE 1: Detection View
          <div className="w-full glass-panel flex flex-col items-center justify-center p-10 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-b from-accent-primary/5 to-transparent"></div>
            
            <div className="w-32 h-32 rounded-full border-4 border-accent-primary/20 border-t-accent-primary animate-spin mb-8 flex items-center justify-center relative z-10">
              <div className="w-24 h-24 rounded-full bg-accent-primary/10 flex items-center justify-center">
                <Loader2 size={40} className="text-accent-primary animate-pulse" />
              </div>
            </div>
            
            <h3 className="text-2xl font-bold text-white mb-2 relative z-10">Initializing Pipeline</h3>
            <p className="text-gray-400 text-center max-w-md relative z-10">
              MangaLens is analyzing the batch to confidently detect the source language. Watch the live logs below.
            </p>
          </div>
        ) : (
          // PHASE 2: Live Preview View
          <>
            {/* Left: Original Image */}
            <div className="flex-1 glass-panel flex flex-col overflow-hidden">
              <div className="bg-black/40 px-4 py-3 border-b border-white/5 flex items-center justify-between flex-shrink-0">
                <span className="text-sm font-medium text-gray-300">Original Data</span>
                <ImageIcon size={16} className="text-gray-500" />
              </div>
              <div className="flex-1 p-4 flex items-center justify-center bg-black/20 overflow-hidden relative">
                {currentImage ? (
                  <img 
                    src={`http://localhost:8000/api/images/original?filename=${encodeURIComponent(currentImage)}`}
                    alt="Original"
                    className="max-w-full max-h-full object-contain drop-shadow-2xl rounded"
                    onError={(e) => { e.target.style.display = 'none'; }}
                    onLoad={(e) => { e.target.style.display = 'block'; }}
                  />
                ) : (
                  <Loader2 className="animate-spin text-gray-600" size={32} />
                )}
              </div>
            </div>

            {/* Right: Translated Image */}
            <div className="flex-1 glass-panel flex flex-col overflow-hidden">
              <div className="bg-black/40 px-4 py-3 border-b border-white/5 flex items-center justify-between flex-shrink-0">
                <span className="text-sm font-medium text-accent-primary">Live Output</span>
                <CheckCircle size={16} className="text-accent-primary" />
              </div>
              <div className="flex-1 p-4 flex items-center justify-center bg-black/20 overflow-hidden relative">
                {currentImage ? (
                  <>
                    {/* Skeleton while waiting for image */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-accent-primary/50">
                      <Loader2 className="animate-spin mb-2" size={32} />
                      <span className="text-xs font-mono">Drawing Translations...</span>
                    </div>
                    {/* Actual Image (hidden on error/404) */}
                    <img 
                      key={`${currentImage}-${translatedKey}`}
                      src={`http://localhost:8000/api/images/translated?filename=${encodeURIComponent(currentImage)}&t=${translatedKey}`}
                      alt="Translated"
                      className="max-w-full max-h-full object-contain drop-shadow-2xl rounded relative z-10"
                      onError={(e) => { e.target.style.opacity = 0; }}
                      onLoad={(e) => { e.target.style.opacity = 1; }}
                      style={{ opacity: 0, transition: 'opacity 0.3s ease' }}
                    />
                  </>
                ) : (
                  <Loader2 className="animate-spin text-gray-600" size={32} />
                )}
              </div>
            </div>
          </>
        )}
        
      </div>

      {/* BOTTOM BAR: Logs & Controls */}
      <div className="glass-panel p-4 flex flex-col gap-4 flex-shrink-0">
        <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden relative">
          <div 
            className="bg-gradient-to-r from-accent-primary to-accent-secondary h-full rounded-full transition-all duration-500 relative z-10"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
        
        <div className="flex gap-4 items-stretch h-24">
          <div className="flex-1 bg-black/40 rounded border border-white/5 p-3 font-mono text-[11px] text-gray-400 overflow-y-auto flex flex-col">
            {logs.length > 0 ? (
              // Auto-scroll to bottom behavior
              <div className="mt-auto">
                {logs.slice(-5).map((log, idx) => (
                  <div key={idx} className="truncate leading-tight opacity-80 hover:opacity-100 transition-opacity">
                    {log}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-500 italic mt-auto">Waiting for AI engine...</div>
            )}
          </div>
          
          <button 
            onClick={handleStop}
            className="px-8 flex flex-col items-center justify-center gap-1 bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20 rounded-xl transition-all font-medium"
          >
            <Loader2 size={20} className="animate-spin" />
            <span className="text-sm">Stop</span>
          </button>
        </div>
      </div>
    </div>
  );
}
