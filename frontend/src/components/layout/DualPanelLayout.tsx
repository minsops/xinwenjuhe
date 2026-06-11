import type { ReactNode } from "react";

type Props = {
  left: ReactNode;
  right: ReactNode;
  activePane?: "news" | "analysis";
};

export function DualPanelLayout({ left, right }: Props) {
  return (
    <main className="grid min-h-[calc(100vh-8.5rem)] grid-cols-1 lg:grid-cols-[minmax(420px,1.15fr)_minmax(360px,0.85fr)]">
      <section className="min-w-0 border-b border-stone-300 dark:border-stone-700 lg:border-b-0 lg:border-r">{left}</section>
      <section className="min-w-0">{right}</section>
    </main>
  );
}
