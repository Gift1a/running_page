import type { Distribution } from "../types";
import { formatNumber } from "../utils/format";

type Props = {
  title: string;
  distribution: Distribution;
  mode: "count" | "distance";
  formatLabel: (start: number, end: number) => string;
};

export default function DistributionBars({ title, distribution, mode, formatLabel }: Props) {
  const values = distribution.bins.map((bin) =>
    mode === "count" ? bin.count : bin.distanceM / 1000
  );
  const maxValue = Math.max(1, ...values);

  return (
    <div className="rounded-3xl panel p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-stone-900">{title}</h3>
      <div className="mt-4 space-y-2">
        {distribution.bins.map((bin, index) => {
          const value = mode === "count" ? bin.count : bin.distanceM / 1000;
          const percent = (value / maxValue) * 100;
          return (
            <div
              key={`${bin.start}-${index}`}
              className="grid grid-cols-[5rem,1fr,4.5rem] items-center gap-2 text-xs"
            >
              <div className="truncate text-stone-500">{formatLabel(bin.start, bin.end)}</div>
              <div className="track relative h-2 overflow-hidden rounded-full">
                <div
                  className="h-2 rounded-full bg-amber-400/80"
                  style={{ width: `${percent}%` }}
                />
              </div>
              <div className="whitespace-nowrap text-right text-stone-600 tabular-nums">
                {mode === "count" ? `${value} 次` : `${formatNumber(value, 1)} km`}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
