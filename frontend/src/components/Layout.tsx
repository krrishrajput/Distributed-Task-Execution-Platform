import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Activity, LayoutDashboard, List, Server, GitBranch, Zap, ZapOff } from 'lucide-react';
import { clsx } from 'clsx';
import { useSSE } from '../hooks/useSSE';

export function Layout() {
  const { isConnected } = useSSE();
  
  const navItems = [
    { to: "/", icon: LayoutDashboard, label: "Overview" },
    { to: "/tasks", icon: List, label: "Tasks" },
    { to: "/workers", icon: Server, label: "Workers" },
    { to: "/metrics", icon: Activity, label: "Metrics" },
    { to: "/queue", icon: GitBranch, label: "Queue" },
    { to: "/simulate", icon: Zap, label: "Simulate" },
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-slate-800">
          <Activity className="w-6 h-6 text-blue-500 mr-3" />
          <h1 className="text-xl font-bold tracking-tight text-white">TaskStorm</h1>
        </div>
        
        <nav className="flex-1 py-4">
          <ul className="space-y-1 px-3">
            {navItems.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    clsx(
                      "flex items-center px-3 py-2 text-sm font-medium transition-colors rounded-none",
                      isActive
                        ? "bg-slate-800 text-blue-400"
                        : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
                    )
                  }
                >
                  <item.icon className="w-5 h-5 mr-3 flex-shrink-0" />
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-16 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-6">
          <div className="flex items-center">
            {/* Contextual Title could go here */}
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-sm font-mono">
              <span className="text-slate-400">SYS_STATUS</span>
              {isConnected ? (
                <span className="flex items-center text-green-400">
                  <span className="relative flex h-2 w-2 mr-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                  </span>
                  CONNECTED
                </span>
              ) : (
                <span className="flex items-center text-red-400">
                  <ZapOff className="w-3 h-3 mr-1" />
                  DISCONNECTED
                </span>
              )}
            </div>
            <div className="h-4 w-px bg-slate-700"></div>
            <div className="text-sm font-mono text-slate-400">
              {new Date().toISOString().replace('T', ' ').slice(0, 19)} UTC
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6 bg-slate-950">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
