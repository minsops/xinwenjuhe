import type { ReactNode } from "react";

type Props = {
  left: ReactNode;
  right: ReactNode;
  activePane?: "news" | "analysis";
};

export function DualPanelLayout({ left, right, activePane = "news" }: Props) {
  return (
    <main className="grid min-h-[calc(100vh-8.5rem)] grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.9fr)]">
      <section className={`min-w-0 border-r border-stone-300 dark:border-stone-700 ${activePane === "news" ? "block" : "hidden"} lg:block`}>{left}</section>
      <section className={`min-w-0 ${activePane === "analysis" ? "block" : "hidden"} lg:block`}>{right}</section>
    </main>
  );
}
