import React, { useEffect, useRef, useState } from 'react';
import { Terminal, RefreshCcw } from 'lucide-react';

export default function TerminalLog({ status, onCancel }) {
  const [logs, setLogs] = useState(["Ready to start..."]);
  const logEndRef = useRef(null);

  useEffect(() => {
    let eventSource;
    if (status === 'running') {
      setLogs(["🚀 Connecting to log stream..."]);
      eventSource = new EventSource("http://localhost:8000/api/translate/progress");
      
      eventSource.onmessage = (event) => {
        const data = event.data;
        if (data && data !== "ping") {
          setLogs(prev => [...prev, data]);
        }
      };

      eventSource.onerror = (err) => {
        console.error("SSE Error:", err);
      };
    }

    return () => {
      if (eventSource) eventSource.close();
    };
  }, [status]);

  useEffect(() => {
    // Auto scroll to bottom
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  return (
    <div className="flex-1 bg-black/50 rounded-xl border border-white/5 font-mono text-sm text-gray-300 overflow-hidden flex flex-col relative">
      <div className="bg-white/5 border-b border-white/5 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <Terminal size={14} /> Pipeline Logs
        </div>
        {status === 'running' && (
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1 text-accent-secondary text-xs animate-pulse">
              <RefreshCcw size={12} className="animate-spin" /> Processing
            </span>
          </div>
        )}
      </div>
      
      <div className="flex-1 p-4 overflow-y-auto">
        {logs.map((log, idx) => (
          <div key={idx} className="whitespace-pre-wrap leading-relaxed">{log}</div>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}
