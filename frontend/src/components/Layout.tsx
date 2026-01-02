import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Menu, X } from 'lucide-react';

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/tasks', label: 'Tasks' },
  { to: '/files', label: 'Files' },
  { to: '/watchers', label: 'Watchers' },
  { to: '/settings', label: 'Settings' },
];

export function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  const closeMobile = () => setMobileOpen(false);

  return (
    <div className="min-h-screen lg:flex bg-[#f8fafc]">
      {/* Mobile header */}
      <header className="lg:hidden sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200">
        <div className="flex items-center justify-between px-4 py-3">
          <button
            onClick={() => setMobileOpen(true)}
            className="p-2 rounded-xl hover:bg-slate-100 transition-colors"
            aria-label="Open navigation"
          >
            <Menu size={20} className="text-slate-600" />
          </button>
          <div className="leading-tight">
            <p className="text-sm font-bold text-slate-900">SubAutoTrans</p>
            <p className="text-[10px] text-slate-500 font-medium">Subtitle Translator</p>
          </div>
          <div className="w-9" />
        </div>
      </header>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-64 bg-white border-r border-slate-200 flex-col sticky top-0 h-screen">
        <div className="p-8">
          <div>
            <h1 className="text-lg font-extrabold tracking-tight text-slate-900 leading-none">SubAutoTrans</h1>
            <p className="text-slate-400 text-[11px] font-semibold uppercase tracking-wider mt-1">Translator</p>
          </div>
        </div>

        <nav className="flex-1 px-4 space-y-1">
          {navItems.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
                  isActive
                    ? 'bg-brand-50 text-brand-600 shadow-sm shadow-brand-100/50'
                    : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <span className="font-semibold text-sm">{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-6">
          <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-xs font-bold text-slate-600">System Ready</span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium">Version 1.0.0 (Stable)</p>
          </div>
        </div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
            onClick={closeMobile}
          />
          <aside className="absolute inset-y-0 left-0 w-72 bg-white flex flex-col shadow-2xl animate-in">
            <div className="flex items-center justify-between p-6 border-b border-slate-100">
              <div>
                <h1 className="text-base font-bold text-slate-900">SubAutoTrans</h1>
              </div>
              <button
                onClick={closeMobile}
                className="p-2 rounded-xl hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
                aria-label="Close navigation"
              >
                <X size={18} />
              </button>
            </div>

            <nav className="flex-1 px-4 py-6 space-y-1">
              {navItems.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={closeMobile}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                      isActive
                        ? 'bg-brand-50 text-brand-600 shadow-sm'
                        : 'text-slate-500 hover:bg-slate-50'
                    }`
                  }
                >
                  <span className="font-semibold text-sm">{label}</span>
                </NavLink>
              ))}
            </nav>

            <div className="p-6 border-t border-slate-100">
              <p className="text-xs text-slate-400 font-medium">v1.0.0 Stable Build</p>
            </div>
          </aside>
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 p-4 sm:p-6 lg:p-10 overflow-x-hidden">
        <div className="max-w-7xl mx-auto animate-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
