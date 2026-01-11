import type { CityStat } from "../types";
import { formatDistanceKm } from "../utils/format";

type Props = {
  stats: CityStat[];
  limit?: number;
  options?: number[];
  onLimitChange?: (limit: number) => void;
};

export default function CityStats({ stats, limit, options, onLimitChange }: Props) {
  const limitOptions = options ?? [4, 8, 12];
  const activeLimit = limit ?? limitOptions[0];
  const top = stats.slice(0, activeLimit);
  const maxDistance = Math.max(1, ...top.map((item) => item.distanceM));

  return (
    <section className="rounded-3xl panel p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-stone-500">城市</p>
          <h2 className="text-2xl font-semibold text-stone-900">常跑城市</h2>
        </div>
        {onLimitChange ? (
          <select
            className="control rounded-full px-3 py-1 text-xs text-stone-600"
            value={activeLimit}
            onChange={(event) => onLimitChange(Number(event.target.value))}
          >
            {limitOptions.map((value) => (
              <option key={value} value={value}>
                前 {value}
              </option>
            ))}
          </select>
        ) : (
          <span className="text-xs text-stone-500">前 {top.length}</span>
        )}
      </div>
      {top.length === 0 ? (
        <div className="panel-dashed mt-6 rounded-2xl border border-dashed p-4 text-sm text-stone-500">
          暂无城市数据
        </div>
      ) : (
        <div className="mt-5 space-y-3">
          {top.map((city) => {
            const percent = (city.distanceM / maxDistance) * 100;
            return (
              <div key={`${city.city}-${city.admin1 ?? ""}`} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-stone-800">{city.city}</span>
                  <span className="text-stone-500">{formatDistanceKm(city.distanceM, 1)}</span>
                </div>
                <div className="track h-2 overflow-hidden rounded-full">
                  <div
                    className="h-2 rounded-full bg-teal-500/80"
                    style={{ width: `${percent}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
