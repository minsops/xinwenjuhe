import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  tone?: "neutral" | "green" | "yellow" | "red" | "blue";
};

const tones = {
  neutral: "bg-stone-200 text-stone-800",
  green: "bg-green-100 text-green-900",
  yellow: "bg-yellow-100 text-yellow-900",
  red: "bg-red-100 text-red-900",
  blue: "bg-sky-100 text-sky-900"
};

export function Badge({ children, tone = "neutral" }: Props) {
  return <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}

