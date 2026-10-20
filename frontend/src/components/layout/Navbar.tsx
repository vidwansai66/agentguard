import React, { useEffect, useState } from 'react';
import { Activity, Terminal } from 'lucide-react';
import { api } from '../../api/client';
import { SystemStatus } from '../../types';
import { Link } from 'react-router-dom';
import { ThemeToggle } from '../common/ThemeToggle';

export const Navbar: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const data = await api.getSystemStatus();
      setStatus(data);
    } catch (err) {
      console.error("System status check failed", err);
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 border-b border-dark-border bg-dark-card/85 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between transition-colors duration-200">
      <Link to="/" className="flex items-center gap-3 group">
        <div className="relative w-10 h-10 rounded-xl overflow-hidden p-[1.5px] bg-gradient-to-tr from-emerald-500 via-teal-400 to-emerald-300 shadow-md shadow-emerald-500/25 group-hover:shadow-emerald-500/40 transition-all duration-300 shrink-0">
          <img
            src="/logo.png"
            alt="AgentGuard Cybersecurity AI Logo"
            className="w-full h-full object-cover rounded-[9px] transform group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
            }}
          />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-emerald-400 via-teal-300 to-emerald-200 bg-clip-text text-transparent group-hover:brightness-110 transition-all">
              AgentGuard
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 shadow-sm">
              v1.0.0
            </span>
          </div>
          <p className="text-[11px] text-slate-400 hidden sm:block">AI Reliability & Security Guard</p>
        </div>
      </Link>

      <div className="flex items-center gap-3 sm:gap-4">
        {/* Backend connectivity indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-dark-bg border border-dark-border text-xs transition-colors">
          {status?.database_connected ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-slate-300 dark:text-slate-300 font-medium">Core API Connected</span>
              <span className="text-slate-500 font-mono text-[11px]">({status.database_url_type})</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-rose-500" />
              <span className="text-rose-400 font-medium">API Disconnected</span>
            </>
          )}
        </div>

        {/* Quick Scenario Count Pill */}
        {status && (
          <div className="hidden md:flex items-center gap-2 text-xs text-slate-400 bg-dark-bg/60 px-3 py-1.5 rounded-full border border-dark-border">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>{status.total_scenarios_count} Active Scenarios</span>
          </div>
        )}

        {/* Animated Sun/Moon Toggle from Uiverse.io by JkHuger */}
        <div className="flex items-center px-1">
          <ThemeToggle size="sm" id="navbar-theme-toggle" />
        </div>

        {/* Tactile Launch Run Button (from Uiverse.io by sekaiking) */}
        <Link
          to="/execution"
          className="btn-tactile-brand flex items-center gap-2"
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>Launch Run</span>
        </Link>
      </div>
    </header>
  );
};
