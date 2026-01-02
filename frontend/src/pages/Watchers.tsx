import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { watchersApi, settingsApi } from '../api/client';
import type { FileInfo } from '../api/client';
import { FileBrowser } from '../components/FileBrowser';
import { Eye, EyeOff, Trash2, Plus, Loader2, Folder, XCircle } from 'lucide-react';

export function Watchers() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [selectedDir, setSelectedDir] = useState<FileInfo | null>(null);
  const [targetLanguage, setTargetLanguage] = useState('Chinese');
  const [llmProvider, setLlmProvider] = useState('openai');
  const [defaultsLoaded, setDefaultsLoaded] = useState(false);

  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: settingsApi.get,
  });

  const { data: watchers, isLoading } = useQuery({
    queryKey: ['watchers'],
    queryFn: watchersApi.list,
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

  const createMutation = useMutation({
    mutationFn: () =>
      watchersApi.create({
        path: selectedDir!.path,
        target_language: targetLanguage,
        llm_provider: llmProvider,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchers'] });
      setShowAdd(false);
      setSelectedDir(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: watchersApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchers'] });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: watchersApi.toggle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchers'] });
    },
  });

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-10">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Directory Watchers</h1>
          <p className="text-slate-500 mt-1 font-medium">Automatically translate new files added to these folders.</p>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className={`btn ${showAdd ? 'btn-secondary' : 'btn-primary'} px-6 py-3 shadow-lg ${!showAdd ? 'shadow-brand-200' : ''}`}
        >
          {showAdd ? <Plus size={20} className="rotate-45 transition-transform" /> : <Plus size={20} />}
          <span className="text-sm font-black uppercase tracking-wider">{showAdd ? 'Cancel' : 'Add Watcher'}</span>
        </button>
      </div>

      {/* Add Watcher Form */}
      {showAdd && (
        <div className="card border-brand-100 bg-gradient-to-b from-white to-brand-50/20 mb-10 animate-in">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-brand-50 text-brand-600 rounded-xl flex items-center justify-center border border-brand-100">
              <Plus size={22} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 leading-none">New Watcher</h2>
              <p className="text-xs font-medium text-slate-400 mt-1">Configure a directory to monitor for new files.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
            <div className="space-y-4">
              <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                Select Directory
              </label>
              <div className="card !p-0 overflow-hidden border-slate-200">
                <FileBrowser
                  onSelect={(file) => file.is_dir && setSelectedDir(file)}
                  showOnlyDirs
                />
              </div>
            </div>

            <div className="space-y-6">
              <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
                <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">
                  Monitoring Path
                </label>
                {selectedDir ? (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-brand-50 text-brand-600 rounded-xl flex items-center justify-center border border-brand-100">
                      <Folder size={20} />
                    </div>
                    <div className="min-w-0">
                      <p className="font-bold text-slate-700 truncate">{selectedDir.name}</p>
                      <p className="text-[10px] text-slate-400 font-medium truncate">{selectedDir.path}</p>
                    </div>
                  </div>
                ) : (
                  <div className="py-4 text-center border-2 border-dashed border-slate-100 rounded-xl">
                    <p className="text-xs font-bold text-slate-300 uppercase tracking-widest">No directory selected</p>
                  </div>
                )}
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
              </div>

              <div className="pt-2">
                <button
                  onClick={() => createMutation.mutate()}
                  disabled={!selectedDir || createMutation.isPending}
                  className="btn btn-primary w-full py-4 shadow-xl shadow-brand-200"
                >
                  {createMutation.isPending ? (
                    <Loader2 className="animate-spin" size={20} />
                  ) : (
                    <Plus size={20} />
                  )}
                  <span className="text-base font-black uppercase tracking-wider">Create Watcher</span>
                </button>

                {createMutation.isError && (
                  <div className="mt-4 p-3 bg-rose-50 rounded-xl border border-rose-100">
                    <p className="text-xs font-bold text-rose-600 flex items-start gap-2">
                      <XCircle size={14} className="mt-0.5 flex-shrink-0" />
                      {(createMutation.error as Error).message}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Watchers List */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <Loader2 className="animate-spin text-brand-600" size={40} />
          <p className="text-sm font-bold text-slate-400 animate-pulse uppercase tracking-widest">Loading Watchers...</p>
        </div>
      ) : watchers?.length === 0 ? (
        <div className="card text-center py-20 flex flex-col items-center gap-4 bg-slate-50/50 border-dashed">
          <div className="w-20 h-20 bg-white rounded-3xl flex items-center justify-center shadow-sm border border-slate-100">
            <Eye className="text-slate-200" size={40} />
          </div>
          <div>
            <p className="text-slate-600 font-bold text-lg">No active watchers</p>
            <p className="text-sm text-slate-400 font-medium mt-1 max-w-xs mx-auto">
              Add a watcher to automatically translate new subtitle files in specific directories.
            </p>
          </div>
          <button
            onClick={() => setShowAdd(true)}
            className="btn btn-secondary mt-2 px-6"
          >
            Add your first watcher
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {watchers?.map((watcher) => (
            <div key={watcher.id} className="card card-hover flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between group">
              <div className="flex items-center gap-4 min-w-0 flex-1">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center border transition-all ${
                  watcher.enabled 
                  ? 'bg-emerald-50 text-emerald-600 border-emerald-100' 
                  : 'bg-slate-50 text-slate-400 border-slate-100 opacity-60'
                }`}>
                  {watcher.enabled ? <Eye size={24} /> : <EyeOff size={24} />}
                </div>
                <div className="min-w-0">
                  <h3 className="font-bold text-slate-900 truncate tracking-tight">{watcher.path}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                      {watcher.target_language}
                    </span>
                    <div className="w-1 h-1 rounded-full bg-slate-200" />
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                      {watcher.llm_provider}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => toggleMutation.mutate(watcher.id)}
                  className={`btn px-6 py-2.5 ${
                    watcher.enabled 
                    ? 'bg-slate-100 text-slate-600 hover:bg-slate-200' 
                    : 'btn-primary'
                  }`}
                >
                  <span className="text-xs font-black uppercase tracking-wider">
                    {watcher.enabled ? 'Disable' : 'Enable'}
                  </span>
                </button>
                <button
                  onClick={() => deleteMutation.mutate(watcher.id)}
                  className="p-3 text-slate-300 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all"
                  title="Delete watcher"
                >
                  <Trash2 size={20} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
