import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Bot,
  FlaskConical,
  PlayCircle,
  Clock,
  Wrench,
  GitCompare,
  Settings,
  ShieldCheck
} from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/agents', label: 'Agents', icon: Bot },
  { to: '/scenarios', label: 'Test Scenarios', icon: FlaskConical },
  { to: '/execution', label: 'Run Execution', icon: PlayCircle },
  { to: '/runs', label: 'Runs & Traces', icon: Clock },
  { to: '/repairs', label: 'Diagnosis & Repair', icon: Wrench },
  { to: '/comparison', label: 'Comparison', icon: GitCompare },
  { to: '/settings', label: 'Settings & Docs', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 border-r border-dark-border bg-dark-bg/95 flex flex-col justify-between p-4 shrink-0 transition-colors duration-200">
      <div className="space-y-6">
        <div className="px-3 py-1">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 font-mono">
            Navigation
          </p>
        </div>

        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-brand-500/15 text-brand-600 dark:text-brand-400 border border-brand-500/30 shadow-sm shadow-brand-500/10 font-semibold'
                      : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-dark-card/60'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Security core hypothesis callout banner */}
      <div className="p-3.5 rounded-xl bg-dark-card border border-dark-border/80 text-xs space-y-2 shadow-sm transition-colors">
        <div className="flex items-center gap-2 text-emerald-400 font-semibold">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Security Invariant</span>
          </span>
        </div>
        <p className="text-slate-400 text-[11px] leading-relaxed">
          State-aware recovery & safety checks eliminate tool failure side effects without unbounded latency.
        </p>
      </div>
    </aside>
  );
};
