import type { ReactNode } from "react";

type Props = {
  left: ReactNode;
  right: ReactNode;
  activePane?: "news" | "analysis";
};

export function DualPanelLayout({ left, right }: Props) {
  return (
    <main className="grid min-h-[680px] grid-cols-1 gap-4 lg:grid-cols-[minmax(420px,1.08fr)_minmax(380px,0.92fr)] xl:h-[calc(100vh-16rem)] xl:min-h-0">
      <section className="min-w-0 overflow-hidden rounded-3xl border border-white/70 bg-white shadow-sm dark:border-stone-800 dark:bg-stone-950">{left}</section>
      <section className="min-w-0 overflow-hidden rounded-3xl border border-white/70 bg-white shadow-sm dark:border-stone-800 dark:bg-stone-950">{right}</section>
    </main>
  );
}
