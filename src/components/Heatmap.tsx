import { useMemo } from "react";
import type { Daily } from "../types";
import { formatDistanceKm, formatDuration, formatPace } from "../utils/format";

type Props = {
  daily: Daily[];
  year: number;
  years: number[];
  onYearChange: (year: number) => void;
};

const DAY_MS = 24 * 60 * 60 * 1000;

function buildTooltip(date: string, entry?: Daily): string {
  if (!entry) {
    return date;
  }
  const lines = [date];
  entry.activities.forEach((activity) => {
    const parts = [
      formatDistanceKm(activity.distanceM, 2),
      formatPace(activity.paceSecPerKm),
      formatDuration(activity.durationS),
    ];
    if (activity.avgHr) {
      parts.push(`${Math.round(activity.avgHr)} 次/分`);
    }
    lines.push(parts.join(" | "));
  });
  return lines.join("\n");
}

function heatClass(distance: number, maxDistance: number): string {
  if (!distance || distance <= 0 || maxDistance <= 0) {
    return "heat-empty";
  }
  const ratio = distance / maxDistance;
  if (ratio < 0.25) return "bg-emerald-200";
  if (ratio < 0.5) return "bg-emerald-300";
  if (ratio < 0.75) return "bg-emerald-400";
  return "bg-emerald-500";
}

export default function Heatmap({ daily, year, years, onYearChange }: Props) {
  const { cells, maxDistance } = useMemo(() => {
    const dailyMap = new Map(daily.map((entry) => [entry.date, entry]));
    const yearEntries = daily.filter((entry) => entry.date.startsWith(String(year)));
    const max = Math.max(0, ...yearEntries.map((entry) => entry.distanceM));

    const yearStart = new Date(Date.UTC(year, 0, 1));
    const yearEnd = new Date(Date.UTC(year, 11, 31));
    const startOffset = yearStart.getUTCDay();
    const endOffset = 6 - yearEnd.getUTCDay();

    const gridStart = new Date(yearStart.getTime() - startOffset * DAY_MS);
    const gridEnd = new Date(yearEnd.getTime() + endOffset * DAY_MS);

    const items = [];
    for (let ts = gridStart.getTime(); ts <= gridEnd.getTime(); ts += DAY_MS) {
      const date = new Date(ts).toISOString().slice(0, 10);
      const entry = dailyMap.get(date);
      items.push({ date, entry });
    }

    return { cells: items, maxDistance: max };
  }, [daily, year]);

  return (
    <section className="rounded-3xl panel p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-stone-500">热力图</p>
          <h2 className="text-2xl font-semibold text-stone-900">跑步日历</h2>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-stone-500">年份</span>
          <select
            className="control rounded-full px-3 py-1 text-sm"
            value={year}
            onChange={(event) => onYearChange(Number(event.target.value))}
          >
            {years.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="mt-6 overflow-x-auto">
        <div className="grid grid-flow-col grid-rows-7 gap-x-0 gap-y-1">
          {cells.map((cell) => {
            const distance = cell.entry?.distanceM ?? 0;
            return (
              <div
                key={cell.date}
                title={buildTooltip(cell.date, cell.entry)}
                className={`heat-cell h-3 w-3 rounded-[3px] ${heatClass(distance, maxDistance)} transition hover:scale-110`}
              />
            );
          })}
        </div>
      </div>
      <div className="mt-4 flex items-center justify-end gap-2 text-xs text-stone-500">
        <span>少</span>
        <span className="heat-cell heat-empty h-3 w-3 rounded-[3px]" />
        <span className="heat-cell h-3 w-3 rounded-[3px] bg-emerald-200" />
        <span className="heat-cell h-3 w-3 rounded-[3px] bg-emerald-300" />
        <span className="heat-cell h-3 w-3 rounded-[3px] bg-emerald-400" />
        <span className="heat-cell h-3 w-3 rounded-[3px] bg-emerald-500" />
        <span>多</span>
      </div>
    </section>
  );
}
