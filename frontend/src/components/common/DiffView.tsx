import React from 'react';

interface Props {
  diff: string;
}

export const DiffView: React.FC<Props> = ({ diff }) => {
  const lines = (diff || '').split('\n');

  return (
    <div className="rounded-lg overflow-hidden border border-dark-border bg-[#070A10] font-mono text-xs shadow-inner">
      <div className="bg-dark-card/90 px-4 py-2 border-b border-dark-border flex items-center justify-between text-slate-400 text-[11px]">
        <span>Unified Patch Diff</span>
        <span className="text-slate-500">{lines.length} lines</span>
      </div>
      <div className="p-3 overflow-x-auto max-h-80 leading-5">
        {lines.map((line, idx) => {
          let lineClass = 'text-slate-300';

          if (line.startsWith('+') && !line.startsWith('+++')) {
            lineClass = 'bg-emerald-950/40 text-emerald-300 font-medium';
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            lineClass = 'bg-rose-950/40 text-rose-300 font-medium';
          } else if (line.startsWith('@@')) {
            lineClass = 'text-emerald-400 font-semibold bg-emerald-950/30';
          } else if (line.startsWith('---') || line.startsWith('+++')) {
            lineClass = 'text-slate-500 font-bold';
          }

          return (
            <div key={idx} className={`px-2 py-0.5 rounded-sm flex items-start ${lineClass}`}>
              <span className="w-8 select-none text-slate-600 text-[10px] text-right pr-3 shrink-0">
                {idx + 1}
              </span>
              <span className="whitespace-pre">{line}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
