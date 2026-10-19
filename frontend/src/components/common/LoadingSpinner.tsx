import React from 'react';
import { Loader2 } from 'lucide-react';

interface Props {
  message?: string;
}

export const LoadingSpinner: React.FC<Props> = ({ message = 'Loading...' }) => {
  return (
    <div className="py-20 flex flex-col items-center justify-center text-slate-400 space-y-3">
      <Loader2 className="w-8 h-8 text-sky-400 animate-spin" />
      <p className="text-xs font-mono">{message}</p>
    </div>
  );
};
