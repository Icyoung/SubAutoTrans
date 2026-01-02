import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsApi } from '../api/client';
import type { Settings as SettingsType } from '../api/client';
import { Save, Loader2, CheckCircle, XCircle, Settings as SettingsIcon } from 'lucide-react';

export function Settings() {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<Partial<SettingsType>>({});
  const [testStatus, setTestStatus] = useState<
    Record<string, { state: 'idle' | 'loading' | 'success' | 'error'; message?: string }>
  >({});

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: settingsApi.get,
  });

  const { data: providers } = useQuery({
    queryKey: ['llmProviders'],
    queryFn: settingsApi.getLlmProviders,
  });

  const selectedProvider = formData.default_llm || providers?.providers[0]?.id || 'openai';

  const { data: languages } = useQuery({
    queryKey: ['languages'],
    queryFn: settingsApi.getLanguages,
  });

  useEffect(() => {
    if (settings) {
      setFormData(settings);
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: settingsApi.update,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const handleTest = async (provider: string) => {
    setTestStatus((prev) => ({ ...prev, [provider]: { state: 'loading' } }));

    try {
      if (provider === 'openai') {
        await settingsApi.testLlm({
          provider,
          api_key: formData.openai_api_key,
          model: formData.openai_model,
          base_url: formData.openai_base_url,
        });
      } else if (provider === 'claude') {
        await settingsApi.testLlm({
          provider,
          api_key: formData.claude_api_key,
          model: formData.claude_model,
        });
      } else if (provider === 'deepseek') {
        await settingsApi.testLlm({
          provider,
          api_key: formData.deepseek_api_key,
          model: formData.deepseek_model,
          base_url: formData.deepseek_base_url,
        });
      } else if (provider === 'glm') {
        await settingsApi.testLlm({
          provider,
          api_key: formData.glm_api_key,
          model: formData.glm_model,
          base_url: formData.glm_base_url,
        });
      }

      setTestStatus((prev) => ({
        ...prev,
        [provider]: { state: 'success' },
      }));
    } catch (error) {
      setTestStatus((prev) => ({
        ...prev,
        [provider]: {
          state: 'error',
          message: (error as Error).message,
        },
      }));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(formData);
  };

  const handleChange = (key: keyof SettingsType, value: any) => {
    setFormData((prev) => {
      if (key === 'subtitle_output_format') {
        const next = { ...prev, subtitle_output_format: value };
        if (value !== 'mkv') {
          next.overwrite_mkv = false;
        }
        return next;
      }

      if (key === 'overwrite_mkv') {
        const next = { ...prev, overwrite_mkv: value };
        if (value) {
          next.subtitle_output_format = 'mkv';
        }
        return next;
      }

      return { ...prev, [key]: value };
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="animate-spin text-gray-400" size={32} />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-10">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Settings</h1>
        <p className="text-slate-500 mt-1 font-medium">Configure your translation preferences and API connections.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8 max-w-4xl">
        {/* LLM Settings */}
        <div className="card border-brand-100/50 bg-gradient-to-b from-white to-slate-50/30">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-brand-50 text-brand-600 rounded-xl flex items-center justify-center border border-brand-100">
              <SettingsIcon size={20} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 leading-none">LLM Configuration</h2>
              <p className="text-xs font-medium text-slate-400 mt-1">Choose one provider and configure its credentials.</p>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 ml-1">
                Active LLM Provider
              </label>
              <select
                value={selectedProvider}
                onChange={(e) => handleChange('default_llm', e.target.value)}
                className="select shadow-sm"
              >
                {providers?.providers.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-bold text-slate-800">
                  Provider Settings
                </h3>
              </div>

              {selectedProvider === 'openai' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
                      API Key
                    </label>
                    <input
                      type="password"
                      value={formData.openai_api_key || ''}
                      onChange={(e) => handleChange('openai_api_key', e.target.value)}
                      className="input"
                      placeholder="sk-..."
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
                      Model
                    </label>
                    <select
                      value={formData.openai_model || ''}
                      onChange={(e) => handleChange('openai_model', e.target.value)}
                      className="select"
                    >
                      {providers?.providers
                        .find((p) => p.id === 'openai')
                        ?.models.map((model) => (
                          <option key={model} value={model}>
                            {model}
                          </option>
                        ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
                      Custom API Base URL
                    </label>
                    <input
                      type="text"
                      value={formData.openai_base_url || ''}
                      onChange={(e) => handleChange('openai_base_url', e.target.value)}
                      className="input"
                      placeholder="https://api.openai.com/v1"
                    />
                  </div>
                </div>
              )}

              {selectedProvider === 'claude' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
                      API Key
                    </label>
                    <input
                      type="password"
                      value={formData.claude_api_key || ''}
                      onChange={(e) => handleChange('claude_api_key', e.target.value)}
                      className="input"
                      placeholder="sk-ant-..."
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
                      Model
                    </label>
                    <select
                      value={formData.claude_model || ''}
                      onChange={(e) => handleChange('claude_model', e.target.value)}
                      className="select"
                    >
                      {providers?.providers
                        .find((p) => p.id === 'claude')
                        ?.models.map((model) => (
                          <option key={model} value={model}>
                            {model}
                          </option>
                        ))}
                    </select>
                  </div>
                </div>
              )}

              {selectedProvider === 'deepseek' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
                      API Key
                    </label>
                    <input
                      type="password"
                      value={formData.deepseek_api_key || ''}
                      onChange={(e) => handleChange('deepseek_api_key', e.target.value)}
                      className="input"
                      placeholder="sk-..."
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
                      Model
                    </label>
                    <select
                      value={formData.deepseek_model || ''}
                      onChange={(e) => handleChange('deepseek_model', e.target.value)}
                      className="select"
                    >
                      {providers?.providers
                        .find((p) => p.id === 'deepseek')
                        ?.models.map((model) => (
                          <option key={model} value={model}>
                            {model}
                          </option>
                        ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
                      Custom API Base URL
                    </label>
                    <input
                      type="text"
                      value={formData.deepseek_base_url || ''}
                      onChange={(e) => handleChange('deepseek_base_url', e.target.value)}
                      className="input"
                      placeholder="https://api.deepseek.com"
                    />
                  </div>
                </div>
              )}

              {selectedProvider === 'glm' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
                      API Key
                    </label>
                    <input
                      type="password"
                      value={formData.glm_api_key || ''}
                      onChange={(e) => handleChange('glm_api_key', e.target.value)}
                      className="input"
                      placeholder="glm-..."
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
                      Model
                    </label>
                    <select
                      value={formData.glm_model || ''}
                      onChange={(e) => handleChange('glm_model', e.target.value)}
                      className="select"
                    >
                      {providers?.providers
                        .find((p) => p.id === 'glm')
                        ?.models.map((model) => (
                          <option key={model} value={model}>
                            {model}
                          </option>
                        ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
                      Custom API Base URL
                    </label>
                    <input
                      type="text"
                      value={formData.glm_base_url || ''}
                      onChange={(e) => handleChange('glm_base_url', e.target.value)}
                      className="input"
                      placeholder="https://open.bigmodel.cn/api/paas/v4"
                    />
                  </div>
                </div>
              )}

              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => handleTest(selectedProvider)}
                  className="btn btn-secondary w-full py-2.5"
                  disabled={testStatus[selectedProvider]?.state === 'loading'}
                >
                  {testStatus[selectedProvider]?.state === 'loading' && (
                    <Loader2 className="animate-spin" size={16} />
                  )}
                  Test Connection
                </button>
                {testStatus[selectedProvider]?.state === 'success' && (
                  <p className="text-[10px] font-bold text-emerald-600 mt-2 flex items-center gap-1">
                    <CheckCircle size={12} /> Connected successfully
                  </p>
                )}
                {testStatus[selectedProvider]?.state === 'error' && (
                  <p className="text-[10px] font-bold text-rose-600 mt-2">
                    {testStatus[selectedProvider]?.message}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
        {/* Translation Settings */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="card">
            <h2 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
              <span className="w-1.5 h-6 bg-brand-600 rounded-full" />
              Subtitle Output
            </h2>

            <div className="space-y-6">
              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 ml-1">
                  Default Target Language
                </label>
                <select
                  value={formData.target_language || ''}
                  onChange={(e) => handleChange('target_language', e.target.value)}
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
                  Output Format
                </label>
                <select
                  value={formData.subtitle_output_format || 'mkv'}
                  onChange={(e) => handleChange('subtitle_output_format', e.target.value)}
                  className="select shadow-sm"
                >
                  <option value="mkv">MKV (Embedded)</option>
                  <option value="srt">SRT (External)</option>
                  <option value="ass">ASS (External)</option>
                </select>
              </div>

              <div className="space-y-3">
                <label className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-100 transition-colors">
                  <input
                    type="checkbox"
                    checked={formData.overwrite_mkv || false}
                    onChange={(e) => handleChange('overwrite_mkv', e.target.checked)}
                    className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500/20 border-slate-300"
                    disabled={formData.subtitle_output_format !== 'mkv'}
                  />
                  <span className={`text-sm font-bold ${formData.subtitle_output_format !== 'mkv' ? 'text-slate-300' : 'text-slate-600'}`}>
                    Overwrite Source MKV
                  </span>
                </label>

                <label className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-100 transition-colors">
                  <input
                    type="checkbox"
                    checked={formData.bilingual_output || false}
                    onChange={(e) => handleChange('bilingual_output', e.target.checked)}
                    className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500/20 border-slate-300"
                  />
                  <span className="text-sm font-bold text-slate-600">Bilingual Subtitles</span>
                </label>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
              <span className="w-1.5 h-6 bg-amber-500 rounded-full" />
              System Queue
            </h2>

            <div className="space-y-6">
              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 ml-1">
                  Max Concurrent Tasks
                </label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="1"
                    max="10"
                    step="1"
                    value={formData.max_concurrent_tasks || 2}
                    onChange={(e) => handleChange('max_concurrent_tasks', parseInt(e.target.value))}
                    className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
                  />
                  <span className="w-12 h-12 flex items-center justify-center bg-brand-50 text-brand-600 rounded-xl font-black border border-brand-100 shadow-sm">
                    {formData.max_concurrent_tasks || 2}
                  </span>
                </div>
                <p className="text-[10px] font-medium text-slate-400 mt-3 uppercase tracking-wider">
                  Higher values increase translation speed but may exceed API limits.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Save Button Bar */}
        <div className="sticky bottom-6 card flex items-center justify-between shadow-2xl border-brand-100 bg-white/90 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            {updateMutation.isSuccess && (
              <p className="text-sm font-bold text-emerald-600 flex items-center gap-2 animate-in">
                <CheckCircle size={18} /> Settings saved!
              </p>
            )}
            {updateMutation.isError && (
              <p className="text-sm font-bold text-rose-600 flex items-center gap-2 animate-in">
                <XCircle size={18} /> Error saving settings
              </p>
            )}
          </div>
          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="btn btn-primary px-10 py-3.5 shadow-xl shadow-brand-200"
          >
            {updateMutation.isPending ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              <Save size={20} />
            )}
            <span className="text-base font-black uppercase tracking-wider">Save Configuration</span>
          </button>
        </div>
      </form>
    </div>
  );
}
