import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { tasksApi } from '../api/client';
import { TaskCard } from '../components/TaskCard';
import { Loader2, ChevronLeft, ChevronRight } from 'lucide-react';

const statusFilters = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'paused', label: 'Paused' },
  { value: 'cancelled', label: 'Cancelled' },
];

const PAGE_SIZE = 20;

export function Tasks() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ['tasks', statusFilter, page],
    queryFn: () => tasksApi.list({
      status: statusFilter || undefined,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    }),
    refetchInterval: 5000,
    refetchOnMount: 'always',
    staleTime: 0,
  });

  const tasks = data?.tasks;
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  useEffect(() => {
    if (!tasks) return;
    const taskIds = new Set(tasks.map((task) => task.id));
    setSelectedIds((prev) => {
      const next = new Set<number>();
      prev.forEach((id) => {
        if (taskIds.has(id)) next.add(id);
      });
      return next;
    });
  }, [tasks]);

  const pauseAllMutation = useMutation({
    mutationFn: tasksApi.pauseAll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['taskStats'] });
    },
  });

  const pauseSelectedMutation = useMutation({
    mutationFn: (ids: number[]) => tasksApi.pauseSelected(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['taskStats'] });
    },
  });

  const deleteAllMutation = useMutation({
    mutationFn: tasksApi.deleteAll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['taskStats'] });
      setSelectedIds(new Set());
    },
  });

  const deleteSelectedMutation = useMutation({
    mutationFn: (ids: number[]) => tasksApi.deleteSelected(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['taskStats'] });
      setSelectedIds(new Set());
    },
  });

  const toggleSelectAll = (checked: boolean) => {
    if (!tasks) return;
    if (checked) {
      setSelectedIds(new Set(tasks.map((task) => task.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const toggleSelectOne = (taskId: number, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(taskId);
      else next.delete(taskId);
      return next;
    });
  };

  const selectedCount = selectedIds.size;
  const allSelected = !!tasks?.length && selectedCount === tasks.length;

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-10">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Tasks</h1>
          <p className="text-slate-500 mt-1 font-medium">
            Manage and monitor your subtitle translation progress.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] font-black text-slate-400 uppercase tracking-widest">
            Filter by status
          </span>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setSelectedIds(new Set());
              setPage(1);
            }}
            className="select w-44 shadow-sm"
          >
            {statusFilters.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-6">
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={(e) => toggleSelectAll(e.target.checked)}
            className="w-4 h-4 text-blue-600"
          />
          Select all
        </label>
        {selectedCount > 0 && (
          <span className="text-sm text-slate-400">{selectedCount} selected</span>
        )}
        <button
          className="btn btn-secondary"
          onClick={() => pauseAllMutation.mutate()}
          disabled={pauseAllMutation.isPending || !tasks?.length}
        >
          Pause All
        </button>
        <button
          className="btn btn-danger"
          onClick={() => deleteAllMutation.mutate()}
          disabled={deleteAllMutation.isPending || !tasks?.length}
        >
          Delete All
        </button>
        <button
          className="btn btn-secondary"
          onClick={() => pauseSelectedMutation.mutate(Array.from(selectedIds))}
          disabled={pauseSelectedMutation.isPending || selectedCount === 0}
        >
          Pause Selected
        </button>
        <button
          className="btn btn-danger"
          onClick={() => deleteSelectedMutation.mutate(Array.from(selectedIds))}
          disabled={deleteSelectedMutation.isPending || selectedCount === 0}
        >
          Delete Selected
        </button>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <Loader2 className="animate-spin text-brand-600" size={40} />
          <p className="text-sm font-bold text-slate-400 animate-pulse uppercase tracking-widest">
            Syncing Tasks...
          </p>
        </div>
      ) : tasks?.length === 0 ? (
        <div className="card text-center py-20 flex flex-col items-center gap-4 bg-slate-50/50 border-dashed">
          <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center shadow-sm border border-slate-100">
            <Loader2 className="text-slate-300" size={32} />
          </div>
          <div>
            <p className="text-slate-600 font-bold text-lg">No tasks found</p>
            <p className="text-sm text-slate-400 font-medium mt-1">
              Go to Files to add subtitle files for translation.
            </p>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4">
            {tasks?.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                selected={selectedIds.has(task.id)}
                onSelectChange={(checked) => toggleSelectOne(task.id, checked)}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-4 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn btn-secondary p-2 disabled:opacity-50"
              >
                <ChevronLeft size={20} />
              </button>

              <div className="flex items-center gap-2">
                {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
                  let pageNum: number;
                  if (totalPages <= 7) {
                    pageNum = i + 1;
                  } else if (page <= 4) {
                    pageNum = i + 1;
                  } else if (page >= totalPages - 3) {
                    pageNum = totalPages - 6 + i;
                  } else {
                    pageNum = page - 3 + i;
                  }
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPage(pageNum)}
                      className={`w-10 h-10 rounded-xl text-sm font-bold transition-all ${
                        page === pageNum
                          ? 'bg-brand-600 text-white'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn btn-secondary p-2 disabled:opacity-50"
              >
                <ChevronRight size={20} />
              </button>

              <span className="text-sm text-slate-500 ml-4">
                {total} tasks
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
