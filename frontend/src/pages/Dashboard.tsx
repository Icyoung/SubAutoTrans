import { useQuery } from '@tanstack/react-query';
import { NavLink } from 'react-router-dom';
import { tasksApi } from '../api/client';
import { Clock, Play, CheckCircle, XCircle } from 'lucide-react';

export function Dashboard() {
  const { data: stats } = useQuery({
    queryKey: ['taskStats'],
    queryFn: tasksApi.stats,
    refetchInterval: 5000,
  });

  const { data: recentTasks = [] } = useQuery({
    queryKey: ['tasks', 'recent'],
    queryFn: () => tasksApi.list(),
    select: (data) => (Array.isArray(data) ? data : []),
  });

  const recentFive = recentTasks.slice(0, 5);

  const statItems = [
    { label: 'Pending', value: stats?.pending ?? 0, icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100' },
    { label: 'Processing', value: stats?.processing ?? 0, icon: Play, color: 'text-brand-600', bg: 'bg-brand-50', border: 'border-brand-100' },
    { label: 'Completed', value: stats?.completed ?? 0, icon: CheckCircle, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100' },
    { label: 'Failed', value: stats?.failed ?? 0, icon: XCircle, color: 'text-rose-600', bg: 'bg-rose-50', border: 'border-rose-100' },
  ];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Dashboard</h1>
        <p className="text-slate-500 mt-1 font-medium">Overview of your translation tasks and system status.</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        {statItems.map(({ label, value, icon: Icon, color, bg, border }) => (
          <div key={label} className="card card-hover flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className={`w-12 h-12 ${bg} ${color} rounded-2xl flex items-center justify-center border ${border}`}>
                <Icon size={24} />
              </div>
              <span className="text-3xl font-black text-slate-900 tracking-tight">{value}</span>
            </div>
            <div>
              <p className="text-sm font-bold text-slate-500 uppercase tracking-wider">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Tasks */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-slate-900">Recent Tasks</h2>
          <NavLink to="/tasks" className="text-sm font-bold text-brand-600 hover:text-brand-700 transition-colors">
            View all
          </NavLink>
        </div>

        {recentFive.length === 0 ? (
          <div className="text-center py-12 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
            <p className="text-slate-500 font-medium">No tasks yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-separate border-spacing-y-2">
              <thead>
                <tr className="text-slate-400 text-[11px] font-bold uppercase tracking-wider">
                  <th className="px-4 py-2">File Name</th>
                  <th className="px-4 py-2">Language</th>
                  <th className="px-4 py-2">Provider</th>
                  <th className="px-4 py-2 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {recentFive.map((task) => (
                  <tr key={task.id} className="group hover:bg-slate-50 transition-colors rounded-xl overflow-hidden">
                    <td className="px-4 py-4 rounded-l-xl border-y border-l border-transparent group-hover:border-slate-100">
                      <div className="flex flex-col">
                        <span className="font-bold text-slate-700 truncate max-w-[200px]">{task.file_name}</span>
                        <span className="text-[10px] text-slate-400 font-medium truncate max-w-[200px]">{task.file_path}</span>
                      </div>
                    </td>
                    <td className="px-4 py-4 border-y border-transparent group-hover:border-slate-100">
                      <span className="font-semibold text-slate-600">{task.target_language}</span>
                    </td>
                    <td className="px-4 py-4 border-y border-transparent group-hover:border-slate-100">
                      <span className="inline-flex items-center px-2 py-1 rounded-md bg-slate-100 text-slate-600 text-[10px] font-bold uppercase tracking-tight">
                        {task.llm_provider}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-right rounded-r-xl border-y border-r border-transparent group-hover:border-slate-100">
                      <div className="flex items-center justify-end gap-3">
                        {task.status === 'processing' && (
                          <div className="flex flex-col items-end gap-1">
                            <span className="text-[10px] font-black text-brand-600">{task.progress}%</span>
                            <div className="w-12 h-1 bg-slate-100 rounded-full overflow-hidden">
                              <div className="bg-brand-500 h-full rounded-full" style={{ width: `${task.progress}%` }} />
                            </div>
                          </div>
                        )}
                        <span className={`badge ${
                          task.status === 'completed' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' :
                          task.status === 'processing' ? 'bg-brand-50 text-brand-700 border border-brand-100' :
                          task.status === 'failed' ? 'bg-rose-50 text-rose-700 border border-rose-100' :
                          'bg-slate-50 text-slate-700 border border-slate-100'
                        }`}>
                          {task.status}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
