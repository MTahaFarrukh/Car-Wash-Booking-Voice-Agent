import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton-shimmer rounded-md", className)} />;
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-14 w-full" />
      ))}
    </div>
  );
}

export function StatSkeleton() {
  return (
    <div className="rounded-lg border border-border p-5">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="mt-3 h-8 w-16" />
    </div>
  );
}
