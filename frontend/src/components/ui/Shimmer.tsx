import { clsx } from 'clsx';

interface ShimmerProps {
  className?: string;
}

export function Shimmer({ className }: ShimmerProps) {
  return (
    <div 
      className={clsx(
        "relative overflow-hidden bg-slate-800/50 rounded-lg",
        className
      )}
    >
      <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-slate-700/20 to-transparent" />
    </div>
  );
}

export function PipelineSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex gap-4 mb-8">
        <Shimmer className="h-2 w-1/4" />
        <Shimmer className="h-2 w-1/4" />
        <Shimmer className="h-2 w-1/4" />
        <Shimmer className="h-2 w-1/4" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="card p-6 border border-slate-800 bg-slate-900/50 space-y-4">
             <Shimmer className="h-6 w-3/4" />
             <Shimmer className="h-4 w-full" />
             <Shimmer className="h-4 w-5/6" />
             <div className="flex justify-between items-center mt-4 pt-4 border-t border-slate-800">
               <Shimmer className="h-8 w-24 rounded-md" />
               <Shimmer className="h-6 w-16" />
             </div>
          </div>
        ))}
      </div>
    </div>
  );
}
