import React from 'react';
import { CheckCircle2, XCircle, Clock, AlertTriangle, ShieldAlert } from 'lucide-react';

interface Props {
  status: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<Props> = ({ status, size = 'sm' }) => {
  const norm = (status || '').toLowerCase();

  const sizeClasses = size === 'sm' ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1';

  if (norm === 'passed' || norm === 'success' || norm === 'verified_passed') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 ${sizeClasses}`}>
        <CheckCircle2 className="w-3 h-3" />
        <span className="capitalize">{norm === 'verified_passed' ? 'Verified Passed' : 'Passed'}</span>
      </span>
    );
  }

  if (norm === 'failed' || norm === 'error' || norm === 'verified_failed') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/25 ${sizeClasses}`}>
        <XCircle className="w-3 h-3" />
        <span className="capitalize">{norm === 'verified_failed' ? 'Verified Failed' : 'Failed'}</span>
      </span>
    );
  }

  if (norm === 'running' || norm === 'verifying') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/25 ${sizeClasses}`}>
        <Clock className="w-3 h-3 animate-spin" />
        <span className="capitalize">{norm}</span>
      </span>
    );
  }

  if (norm === 'trade_offs_detected' || norm === 'warning') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/25 ${sizeClasses}`}>
        <AlertTriangle className="w-3 h-3" />
        <span className="capitalize">Trade-offs</span>
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-slate-800 text-slate-300 border border-slate-700 ${sizeClasses}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
      <span className="capitalize">{status || 'Pending'}</span>
    </span>
  );
};
