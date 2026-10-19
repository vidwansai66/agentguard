import React from 'react';

interface Props {
  severity: 'low' | 'medium' | 'high' | 'critical' | string;
}

export const SeverityBadge: React.FC<Props> = ({ severity }) => {
  const norm = (severity || '').toLowerCase();

  const styles: Record<string, string> = {
    low: 'bg-slate-800 text-slate-300 border-slate-700',
    medium: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    high: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
    critical: 'bg-rose-500/15 text-rose-400 border-rose-500/40'
  };

  const selected = styles[norm] || styles.low;

  return (
    <span className={`inline-flex items-center text-[10px] uppercase font-mono font-bold tracking-wider px-2 py-0.5 rounded border ${selected}`}>
      {severity}
    </span>
  );
};
