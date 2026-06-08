type Props = {
  value: number;
  max?: number;
};

export function ProgressBar({ value, max = 100 }: Props) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  return (
    <div className="h-2 w-full overflow-hidden rounded bg-stone-200" aria-label={`${pct}%`}>
      <div className="h-full bg-civic" style={{ width: `${pct}%` }} />
    </div>
  );
}

