import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { filesApi } from '../api/client';
import type { FileInfo } from '../api/client';
import { Folder, File, ChevronUp, Loader2, Plus } from 'lucide-react';

interface FileBrowserProps {
  onSelect: (file: FileInfo) => void;
  showOnlyDirs?: boolean;
}

export function FileBrowser({ onSelect, showOnlyDirs = false }: FileBrowserProps) {
  const [currentPath, setCurrentPath] = useState('~');

  const { data, isLoading } = useQuery({
    queryKey: ['files', currentPath],
    queryFn: () => filesApi.browse(currentPath),
  });

  const items = showOnlyDirs
    ? data?.items.filter((item) => item.is_dir)
    : data?.items;

  return (
    <div className="bg-white">
      {/* Header */}
      <div className="bg-slate-50/50 px-5 py-3 border-b border-slate-200 flex items-center gap-3">
        {data?.parent_path && (
          <button
            onClick={() => setCurrentPath(data.parent_path!)}
            className="p-1.5 hover:bg-slate-200/50 text-slate-500 rounded-lg transition-colors"
            title="Go up"
          >
            <ChevronUp size={18} />
          </button>
        )}
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none mb-1">Current Path</p>
          <p className="text-sm font-bold text-slate-600 truncate">
            {data?.current_path || currentPath}
          </p>
        </div>
      </div>

      {/* File list */}
      <div className="max-h-96 overflow-y-auto overflow-x-hidden">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Loader2 className="animate-spin text-brand-600" size={32} />
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest animate-pulse">Loading files...</p>
          </div>
        ) : items?.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-slate-400 font-bold">Empty folder</p>
            <p className="text-[10px] font-black text-slate-300 uppercase tracking-widest mt-1">No {showOnlyDirs ? 'directories' : 'files'} found</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {items?.map((item) => (
              <button
                key={item.path}
                onClick={() => {
                  if (item.is_dir) {
                    setCurrentPath(item.path);
                  }
                  onSelect(item);
                }}
                className="w-full px-5 py-4 flex items-center gap-4 hover:bg-slate-50 transition-colors text-left group"
              >
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110 ${
                  item.is_dir ? 'bg-brand-50 text-brand-600 border border-brand-100' : 'bg-slate-50 text-slate-400 border border-slate-100'
                }`}>
                  {item.is_dir ? (
                    <Folder size={20} />
                  ) : (
                    <File size={20} />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-slate-700 truncate group-hover:text-brand-600 transition-colors">{item.name}</p>
                  {item.size !== null && (
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-tight mt-0.5">
                      {formatSize(item.size)}
                    </p>
                  )}
                </div>
                <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                  <Plus size={16} className="text-brand-500" />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
}
