import React, { useState, useEffect } from 'react';
import { Folder, ChevronRight, X, ArrowUpCircle } from 'lucide-react';

export default function FolderBrowserModal({ isOpen, onClose, onSelect }) {
  const [currentPath, setCurrentPath] = useState('root');
  const [parentPath, setParentPath] = useState('');
  const [folders, setFolders] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadDirectory('root');
    }
  }, [isOpen]);

  const loadDirectory = async (path) => {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/browse?path=${encodeURIComponent(path)}`);
      const data = await res.json();
      setCurrentPath(data.path);
      setParentPath(data.parent);
      setFolders(data.folders || []);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="glass-panel w-[600px] max-h-[80vh] flex flex-col overflow-hidden animate-slide-up shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-glass-border bg-white/5">
          <h3 className="text-lg font-medium text-white flex items-center gap-2">
            <Folder className="text-accent-primary" size={20} /> Select Folder
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-full transition-colors">
            <X size={20} className="text-gray-400" />
          </button>
        </div>

        {/* Path Breadcrumb */}
        <div className="px-6 py-3 bg-black/30 border-b border-glass-border flex items-center gap-2 text-sm text-gray-300">
          <span className="truncate">{currentPath === 'root' ? 'This PC' : currentPath}</span>
        </div>

        {/* Folder List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-1 min-h-[300px]">
          {loading ? (
            <div className="flex items-center justify-center h-full text-gray-400">Loading...</div>
          ) : (
            <>
              {currentPath !== 'root' && (
                <div 
                  onClick={() => loadDirectory(parentPath)}
                  className="flex items-center gap-3 p-3 hover:bg-white/10 rounded-lg cursor-pointer transition-colors text-gray-300"
                >
                  <ArrowUpCircle size={20} className="text-gray-400" />
                  <span>.. (Up a directory)</span>
                </div>
              )}
              {folders.map((folder, idx) => (
                <div 
                  key={idx}
                  onClick={() => loadDirectory(folder.path)}
                  className="flex items-center justify-between p-3 hover:bg-white/10 rounded-lg cursor-pointer transition-colors group"
                >
                  <div className="flex items-center gap-3 text-gray-200">
                    <Folder size={20} className="text-accent-secondary" />
                    <span className="truncate max-w-[400px]">{folder.name}</span>
                  </div>
                  <ChevronRight size={16} className="text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              ))}
              {folders.length === 0 && currentPath !== 'root' && (
                <div className="text-center text-gray-500 mt-10">Folder is empty</div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-glass-border bg-black/30 flex justify-end gap-3">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button 
            onClick={() => onSelect(currentPath)}
            disabled={currentPath === 'root'} 
            className="btn-primary"
          >
            Select Current Folder
          </button>
        </div>
      </div>
    </div>
  );
}
