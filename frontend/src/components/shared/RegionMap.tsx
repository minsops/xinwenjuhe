import { regionColors } from "../../utils/regionColors";

type Props = {
  regions: string[];
};

export function RegionMap({ regions }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {regions.map((region) => (
        <span key={region} className={`rounded px-2 py-1 text-xs ${regionColors[region] ?? "bg-stone-200 text-stone-900"}`}>
          {region.replace("_", " ")}
        </span>
      ))}
    </div>
  );
}

