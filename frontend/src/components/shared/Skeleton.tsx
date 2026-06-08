type Props = {
  lines?: number;
};

export function Skeleton({ lines = 4 }: Props) {
  return (
    <div className="space-y-3 p-5" aria-busy="true">
      {Array.from({ length: lines }, (_, index) => (
        <div
          key={index}
          className="h-4 animate-pulse rounded bg-stone-200 dark:bg-stone-800"
          style={{ width: `${Math.max(35, 92 - index * 12)}%` }}
        />
      ))}
    </div>
  );
}
