import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { tasksApi, settingsApi } from '../api/client';
import type { FileInfo } from '../api/client';
import { FileBrowser } from '../components/FileBrowser';
import { Plus, FolderPlus, Loader2, File, Settings, XCircle, CheckCircle } from 'lucide-react';

export function Files() {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<FileInfo | null>(null);
  const [targetLanguage, setTargetLanguage] = useState('Chinese');
  const [llmProvider, setLlmProvider] = useState('openai');
  const [mode, setMode] = useState<'file' | 'directory'>('file');
  const [recursive, setRecursive] = useState(false);
  const [forceOverride, setForceOverride] = useState(false);
  const [defaultsLoaded, setDefaultsLoaded] = useState(false);

  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: settingsApi.get,
  });

  const { data: languages } = useQuery({
    queryKey: ['languages'],
    queryFn: settingsApi.getLanguages,
  });

  const { data: providers } = useQuery({
    queryKey: ['llmProviders'],
    queryFn: settingsApi.getLlmProviders,
  });

  useEffect(() => {
    if (settings && !defaultsLoaded) {
      setTargetLanguage(settings.target_language);
      setLlmProvider(settings.default_llm);
      setDefaultsLoaded(true);
    }
  }, [settings, defaultsLoaded]);

  const createTaskMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile) throw new Error('No file selected');

      if (mode === 'directory') {
        return tasksApi.createFromDirectory({
          directory_path: selectedFile.path,
          target_language: targetLanguage,
          llm_provider: llmProvider,
          recursive,
          force_override: forceOverride,
        });
      }

      return tasksApi.create({
        file_path: selectedFile.path,
        target_language: targetLanguage,
        llm_provider: llmProvider,
        force_override: forceOverride,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['taskStats'] });
      setSelectedFile(null);
    },
  });

  const handleFileSelect = (file: FileInfo) => {
    if (mode === 'file' && !file.is_dir) {
      setSelectedFile(file);
    } else if (mode === 'file' && file.is_dir) {
      setMode('directory');
      setSelectedFile(file);
    } else if (mode === 'directory' && file.is_dir) {
      setSelectedFile(file);
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Add Translation Task</h1>
        <p className="text-slate-500 mt-1 font-medium">Select files or directories to start the translation process.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* File Browser Area */}
        <div className="space-y-6">
          <div className="flex p-1 bg-slate-100 rounded-2xl w-fit">
            <button
              onClick={() => { setMode('file'); setSelectedFile(null); }}
              className={`flex items-center gap-2 px-6 py-2 rounded-xl text-sm font-bold transition-all ${
                mode === 'file' 
                ? 'bg-white text-brand-600 shadow-sm' 
                : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <Plus size={16} />
              Single File
            </button>
            <button
              onClick={() => { setMode('directory'); setSelectedFile(null); }}
              className={`flex items-center gap-2 px-6 py-2 rounded-xl text-sm font-bold transition-all ${
                mode === 'directory' 
                ? 'bg-white text-brand-600 shadow-sm' 
                : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <FolderPlus size={16} />
              Directory
            </button>
          </div>

          <div className="card !p-0 overflow-hidden border-slate-200">
            <FileBrowser
              onSelect={handleFileSelect}
              showOnlyDirs={mode === 'directory'}
            />
          </div>
        </div>

        {/* Task Options Area */}
        <div className="lg:sticky lg:top-8">
          <div className="card border-brand-100 bg-gradient-to-b from-white to-slate-50/50">
            <h2 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
              <Settings className="text-brand-600" size={20} />
              Task Options
            </h2>

            {selectedFile ? (
              <div className="space-y-6">
                <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
                  <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">
                    Selected {mode === 'file' ? 'File' : 'Directory'}
                  </label>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-brand-50 text-brand-600 rounded-xl flex items-center justify-center border border-brand-100">
                      {mode === 'file' ? <File size={20} /> : <FolderPlus size={20} />}
                    </div>
                    <div className="min-w-0">
                      <p className="font-bold text-slate-700 truncate">{selectedFile.name}</p>
                      <p className="text-[10px] text-slate-400 font-medium truncate">{selectedFile.path}</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 ml-1">
                      Target Language
                    </label>
                    <select
                      value={targetLanguage}
                      onChange={(e) => setTargetLanguage(e.target.value)}
                      className="select shadow-sm"
                    >
                      {languages?.languages.map((lang) => (
                        <option key={lang.code} value={lang.code}>
                          {lang.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 ml-1">
                      LLM Provider
                    </label>
                    <select
                      value={llmProvider}
                      onChange={(e) => setLlmProvider(e.target.value)}
                      className="select shadow-sm"
                    >
                      {providers?.providers.map((provider) => (
                        <option key={provider.id} value={provider.id}>
                          {provider.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {mode === 'directory' && (
                    <label className="flex items-center gap-3 p-3 bg-white rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50 transition-colors">
                      <input
                        type="checkbox"
                        checked={recursive}
                        onChange={(e) => setRecursive(e.target.checked)}
                        className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500/20 border-slate-300"
                      />
                      <span className="text-sm font-bold text-slate-600">Include subdirectories</span>
                    </label>
                  )}

                  <label className="flex items-center gap-3 p-3 bg-white rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50 transition-colors">
                    <input
                      type="checkbox"
                      checked={forceOverride}
                      onChange={(e) => setForceOverride(e.target.checked)}
                      className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500/20 border-slate-300"
                    />
                    <div>
                      <span className="text-sm font-bold text-slate-600">Force override</span>
                      <p className="text-xs text-slate-400 mt-0.5">Translate even if target language subtitle exists</p>
                    </div>
                  </label>
                </div>

                <div className="pt-2">
                  <button
                    onClick={() => createTaskMutation.mutate()}
                    disabled={createTaskMutation.isPending}
                    className="btn btn-primary w-full py-3.5 shadow-lg shadow-brand-200"
                  >
                    {createTaskMutation.isPending ? (
                      <Loader2 className="animate-spin" size={20} />
                    ) : (
                      <Plus size={20} />
                    )}
                    <span className="text-base">Create {mode === 'directory' ? 'Tasks' : 'Task'}</span>
                  </button>
                </div>

                {createTaskMutation.isError && (
                  <div className="p-3 bg-rose-50 rounded-xl border border-rose-100">
                    <p className="text-xs font-bold text-rose-600 flex items-start gap-2">
                      <XCircle size={14} className="mt-0.5 flex-shrink-0" />
                      {(createTaskMutation.error as Error).message}
                    </p>
                  </div>
                )}

                {createTaskMutation.isSuccess && (
                  <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100">
                    <p className="text-xs font-bold text-emerald-600 flex items-center gap-2">
                      <CheckCircle size={14} className="flex-shrink-0" />
                      Task{mode === 'directory' ? 's' : ''} created successfully!
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-16 px-6 bg-slate-50/50 rounded-2xl border-2 border-dashed border-slate-200 flex flex-col items-center gap-3">
                <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-sm text-slate-300">
                  <File size={24} />
                </div>
                <div>
                  <p className="text-slate-500 font-bold">No selection</p>
                  <p className="text-[11px] text-slate-400 font-medium mt-1 uppercase tracking-wider">
                    Select a {mode === 'file' ? 'file' : 'directory'} from the browser to continue
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
