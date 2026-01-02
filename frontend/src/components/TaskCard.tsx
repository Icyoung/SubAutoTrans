import { tasksApi } from '../api/client';
import type { Task } from '../api/client';
import {
  Clock,
  Play,
  CheckCircle,
  XCircle,
  Ban,
  Pause,
  RotateCcw,
  Trash2,
} from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

interface TaskCardProps {
  task: Task;
  selected: boolean;
  onSelectChange: (checked: boolean) => void;
}

const statusConfig = {
  pending: { icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100' },
  processing: { icon: Play, color: 'text-brand-600', bg: 'bg-brand-50', border: 'border-brand-100' },
  completed: { icon: CheckCircle, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100' },
  failed: { icon: XCircle, color: 'text-rose-600', bg: 'bg-rose-50', border: 'border-rose-100' },
  cancelled: { icon: Ban, color: 'text-slate-400', bg: 'bg-slate-50', border: 'border-slate-100' },
  paused: { icon: Pause, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100' },
};

export function TaskCard({ task, selected, onSelectChange }: TaskCardProps) {
  const queryClient = useQueryClient();
  const config = statusConfig[task.status];
  const StatusIcon = config.icon;

  const deleteMutation = useMutation({
    mutationFn: () => tasksApi.delete(task.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['taskStats'] });
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => tasksApi.retry(task.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['taskStats'] });
    },
  });

  return (
    <div className="card card-hover overflow-hidden group">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="flex items-start gap-4 flex-1 min-w-0">
          <input
            type="checkbox"
            checked={selected}
            onChange={(e) => onSelectChange(e.target.checked)}
            className="mt-2 w-4 h-4 text-blue-600"
          />
          <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-3">
            <div className={`w-10 h-10 ${config.bg} ${config.color} rounded-xl flex items-center justify-center border ${config.border} flex-shrink-0 transition-transform group-hover:scale-110`}>
              <StatusIcon size={20} />
            </div>
            <div className="min-w-0">
              <h3 className="font-bold text-slate-900 truncate tracking-tight">{task.file_name}</h3>
              <p className="text-[11px] font-medium text-slate-400 truncate mt-0.5">{task.file_path}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 text-[10px] font-bold uppercase tracking-tight">
              {task.llm_provider}
            </span>
            <div className="w-1 h-1 rounded-full bg-slate-300" />
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">
              {task.target_language}
            </span>
            <div className="w-1 h-1 rounded-full bg-slate-300" />
            <span className={`badge ${
              task.status === 'completed' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' :
              task.status === 'processing' ? 'bg-brand-50 text-brand-700 border border-brand-100' :
              task.status === 'failed' ? 'bg-rose-50 text-rose-700 border border-rose-100' :
              task.status === 'paused' ? 'bg-amber-50 text-amber-700 border border-amber-100' :
              'bg-slate-50 text-slate-700 border border-slate-100'
            }`}>
              {task.status}
            </span>
          </div>

          {task.status === 'processing' && (
            <div className="mt-5">
              <div className="flex items-center justify-between text-[11px] font-black mb-1.5">
                <span className="text-slate-400 uppercase tracking-widest">Progress</span>
                <span className="text-brand-600">{task.progress}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 relative overflow-hidden">
                <div
                  className="bg-brand-500 h-full rounded-full transition-all duration-500 ease-out shadow-[0_0_8px_rgba(13,149,232,0.3)]"
                  style={{ width: `${task.progress}%` }}
                />
              </div>
            </div>
          )}

          {task.error_message && (
            <div className="mt-4 p-3 bg-rose-50 rounded-xl border border-rose-100 border-dashed">
              <p className="text-xs font-bold text-rose-600 flex items-start gap-2">
                <XCircle size={14} className="mt-0.5 flex-shrink-0" />
                {task.error_message}
              </p>
            </div>
          )}
          </div>
        </div>

        <div className="flex items-center gap-2 sm:self-start lg:self-center">
          {(task.status === 'failed' || task.status === 'cancelled' || task.status === 'paused') && (
            <button
              onClick={() => retryMutation.mutate()}
              disabled={retryMutation.isPending}
              className="p-2.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-xl transition-all active:scale-95"
              title="Retry"
            >
              <RotateCcw size={18} />
            </button>
          )}

          <button
            onClick={() => deleteMutation.mutate()}
            disabled={deleteMutation.isPending}
            className="p-2.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all active:scale-95"
            title="Delete"
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
