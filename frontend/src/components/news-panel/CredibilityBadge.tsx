import { ShieldCheck } from "lucide-react";

type Props = {
  score?: number | null;
};

export function CredibilityBadge({ score }: Props) {
  const value = score ?? 60;
  const tone = value >= 75 ? "text-green-700" : value >= 50 ? "text-amber-700" : "text-red-700";
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium ${tone}`} title="Credibility score">
      <ShieldCheck className="h-3.5 w-3.5" />
      {value}
    </span>
  );
}

