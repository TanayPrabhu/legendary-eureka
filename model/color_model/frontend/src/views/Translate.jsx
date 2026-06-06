import React, { useState, useEffect, useRef } from 'react';
import { HardDrive, Play, Loader2, FolderOpen, UploadCloud, RefreshCcw, Layers, X } from 'lucide-react';
import FolderBrowserModal from '../components/FolderBrowserModal';

export default function Translate({ onStart }) {
  // Try to load state from localStorage
  const savedConfig = JSON.parse(localStorage.getItem('mangalens_config')) || {};
  const savedMode = localStorage.getItem('mangalens_inputMode');
  const savedUpload = JSON.parse(localStorage.getItem('mangalens_uploadData'));

  const [config, setConfig] = useState({
    inputDir: savedConfig.inputDir || '',
    outputImgDir: savedConfig.outputImgDir || '',
    outputJsonDir: savedConfig.outputJsonDir || '',
    modelPath: savedConfig.modelPath || '',
    wipeMemory: savedConfig.wipeMemory || false
  });
  
  const [models, setModels] = useState([]);
  const [browserTarget, setBrowserTarget] = useState(null);
  
  // UI Modes
  const [inputMode, setInputMode] = useState(savedMode || 'folder'); // 'folder' | 'dragdrop'
  
  // Drag and drop state
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadData, setUploadData] = useState(savedUpload || null); // { count: number, thumbnail: string }
  
  // Save to localStorage on change
  useEffect(() => {
    localStorage.setItem('mangalens_config', JSON.stringify(config));
    localStorage.setItem('mangalens_inputMode', inputMode);
    if (uploadData) {
      localStorage.setItem('mangalens_uploadData', JSON.stringify(uploadData));
    } else {
      localStorage.removeItem('mangalens_uploadData');
    }
  }, [config, inputMode, uploadData]);
  
  // Progress & Logs
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    fetch('http://localhost:8000/api/models')
      .then(res => res.json())
      .then(data => {
        if (data.models) {
          setModels(data.models);
          if (data.models.length > 0) {
            setConfig(prev => ({ ...prev, modelPath: data.models[0].path }));
          }
        }
      })
      .catch(console.error);
  }, []);



  const handleStart = async () => {
    if (inputMode === 'folder' && !config.inputDir) {
      alert("Please select or enter an Input Folder.");
      return;
    }
    if (inputMode === 'dragdrop' && !uploadData) {
      alert("Please drag and drop images first.");
      return;
    }
    if (!config.outputImgDir || !config.outputJsonDir) {
      alert("Please specify the Output Image and JSON folders.");
      return;
    }
    
    try {
      const res = await fetch('http://localhost:8000/api/translate/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input_dir: config.inputDir,
          output_img_dir: config.outputImgDir,
          output_json_dir: config.outputJsonDir,
          model_path: config.modelPath,
          wipe_memory: config.wipeMemory
        })
      });
      const data = await res.json();
      if (!data.success) {
        alert(data.error || "Failed to start");
      } else {
        if (onStart) onStart();
      }
    } catch (err) {
      console.error(err);
      alert("Failed to connect to backend");
    }
  };

  // Upload Logic
  const handleFileUpload = async (files) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setUploadData(null);
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    
    try {
      const res = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        setConfig(prev => ({ ...prev, inputDir: data.input_dir }));
        setUploadData({
          count: data.count,
          thumbnail: data.thumbnail
        });
      }
    } catch (err) {
      alert("Failed to upload images");
    }
    setUploading(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files);
    }
  };

  return (
    <div className="animate-fade-in flex flex-col h-full overflow-y-auto pb-10 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-3xl font-bold text-white tracking-tight">Translate Manga</h2>
        
        {/* MODE TOGGLE */}
        <div className="bg-black/40 p-1 rounded-xl flex items-center gap-1 border border-white/5">
          <button 
            onClick={() => setInputMode('folder')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${inputMode === 'folder' ? 'bg-accent-primary text-white shadow' : 'text-gray-400 hover:text-gray-200'}`}
          >
            Folder Path
          </button>
          <button 
            onClick={() => setInputMode('dragdrop')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${inputMode === 'dragdrop' ? 'bg-accent-primary text-white shadow' : 'text-gray-400 hover:text-gray-200'}`}
          >
            Drag & Drop
          </button>
        </div>
      </div>
      
      <div className="flex flex-col gap-6">
        
        {/* DRAG AND DROP ZONE */}
        {inputMode === 'dragdrop' && (
          <div 
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={onDrop}
            className={`relative flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-2xl transition-all duration-300 animate-fade-in min-h-[280px] ${
              isDragging ? 'border-accent-primary bg-accent-primary/10' : 'border-white/10 bg-black/20 hover:border-white/20'
            }`}
          >
            {uploading ? (
              <div className="flex flex-col items-center text-accent-primary">
                <RefreshCcw size={48} className="animate-spin mb-4" />
                <p className="text-lg font-medium">Uploading images...</p>
              </div>
            ) : uploadData ? (
              <div className="flex flex-col items-center animate-slide-up">
                <div className="relative group cursor-pointer mb-4" onClick={() => setUploadData(null)}>
                  <div className="absolute inset-0 bg-black/50 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center z-20">
                    <X size={32} className="text-white" />
                  </div>
                  <div className="relative z-10 w-32 h-40 bg-gray-800 rounded-xl border-4 border-white shadow-2xl overflow-hidden transform -rotate-6 transition-transform group-hover:rotate-0">
                    {uploadData.thumbnail && <img src={`data:image/jpeg;base64,${uploadData.thumbnail}`} className="w-full h-full object-cover" alt="Preview" />}
                  </div>
                  <div className="absolute top-2 left-2 z-0 w-32 h-40 bg-gray-700 rounded-xl border border-white/20 shadow-lg transform rotate-3"></div>
                  <div className="absolute top-4 left-4 -z-10 w-32 h-40 bg-gray-800 rounded-xl border border-white/10 shadow transform rotate-6"></div>
                </div>
                <p className="text-xl font-bold text-white mb-1"><Layers className="inline mr-2 text-accent-primary" size={24}/>{uploadData.count} Images Ready</p>
                <p className="text-sm text-gray-400">Click the stack to remove and upload different images</p>
              </div>
            ) : (
              <div className="flex flex-col items-center text-gray-400 pointer-events-none">
                <UploadCloud size={48} className="mb-4 text-gray-500" />
                <p className="text-xl font-medium text-gray-300 mb-2">Drag & Drop Images Here</p>
                <p className="text-sm">We will process them automatically</p>
              </div>
            )}
          </div>
        )}



        {/* CONFIGURATION PANEL */}
        <div className="glass-panel p-6 flex flex-col gap-6">
          <h3 className="text-xl font-medium text-white flex items-center gap-2">
            <HardDrive size={20} className="text-accent-primary" /> Configuration
          </h3>
          
          <div className="space-y-5">
            {/* Input Folder (Only show if in Folder mode) */}
            {inputMode === 'folder' && (
              <div className="animate-fade-in">
                <label className="block text-sm font-medium text-gray-400 mb-1">Input Folder (Images)</label>
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={config.inputDir}
                    onChange={e => setConfig({...config, inputDir: e.target.value})}
                    className="input-field flex-1 text-sm font-mono" 
                    placeholder="Enter or paste folder path..." 
                  />
                  <button 
                    onClick={() => setBrowserTarget('inputDir')}
                    className="btn-secondary flex items-center gap-2 px-3"
                  >
                    <FolderOpen size={16} /> Browse
                  </button>
                </div>
              </div>
            )}

            {/* Output Folders (Always show) */}
            {[
              { id: 'outputImgDir', label: 'Output Folder (Translated Images)' },
              { id: 'outputJsonDir', label: 'Output Folder (LabelMe JSONs)' }
            ].map(field => (
              <div key={field.id}>
                <label className="block text-sm font-medium text-gray-400 mb-1">{field.label}</label>
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={config[field.id]}
                    onChange={e => setConfig({...config, [field.id]: e.target.value})}
                    className="input-field flex-1 text-sm font-mono" 
                    placeholder="Enter or paste folder path..." 
                  />
                  <button 
                    onClick={() => setBrowserTarget(field.id)}
                    className="btn-secondary flex items-center gap-2 px-3"
                  >
                    <FolderOpen size={16} /> Browse
                  </button>
                </div>
              </div>
            ))}

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">YOLO Detection Model</label>
              <select 
                value={config.modelPath}
                onChange={e => setConfig({...config, modelPath: e.target.value})}
                className="input-field appearance-none"
              >
                {models.map(m => <option key={m.path} value={m.path}>{m.name}</option>)}
                {models.length === 0 && <option value="">No models found in ../runs/ directory</option>}
              </select>
            </div>

            <div className="pt-2 border-t border-white/5 flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-200">Wipe Translation Memory</div>
                <div className="text-xs text-gray-400">Clear glossary memory for a new manga (Chinese/Korean only).</div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={config.wipeMemory} 
                  onChange={e => setConfig({...config, wipeMemory: e.target.checked})}
                  className="sr-only peer" 
                />
                <div className="w-11 h-6 bg-white/10 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-gray-300 after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent-primary"></div>
              </label>
            </div>
          </div>

          <div className="mt-6">
            <button 
              onClick={handleStart} 
              className="btn-primary w-full py-4 text-lg flex items-center justify-center gap-2"
            >
              <><Play size={24} /> Start Translation</>
            </button>
          </div>
        </div>

      </div>

      <FolderBrowserModal 
        isOpen={browserTarget !== null}
        onClose={() => setBrowserTarget(null)}
        onSelect={(path) => {
          if (browserTarget) {
            setConfig(prev => ({ ...prev, [browserTarget]: path }));
          }
          setBrowserTarget(null);
        }}
      />
    </div>
  );
}
