import React, { useEffect, useState } from 'react';
import { Shield, Activity, Database, RefreshCw, Terminal, CheckCircle2, AlertTriangle } from 'lucide-react';
import { api } from '../../api/client';
import { SystemStatus } from '../../types';
import { Link } from 'react-router-dom';

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
    <header className="h-16 border-b border-dark-border bg-dark-card/80 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-brand-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-sky-500/20">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              AgentGuard
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800/50">
              v1.0.0
            </span>
          </div>
          <p className="text-[11px] text-slate-400 hidden sm:block">AI Reliability & Verified Repair Platform</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Backend connectivity indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-dark-bg border border-dark-border text-xs">
          {status?.database_connected ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-slate-300 font-medium">Core API Connected</span>
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
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span>{status.total_scenarios_count} Active Scenarios</span>
          </div>
        )}

        {/* Quick Launch Run Button */}
        <Link
          to="/execution"
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white transition-all shadow-md shadow-brand-600/20"
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>Launch Run</span>
        </Link>
      </div>
    </header>
  );
};
