import type { Monthly } from "../types";
import { formatDistanceKm, formatMonthLabel } from "../utils/format";

type Props = {
  monthly: Monthly[];
  year: number;
  years: number[];
  onYearChange: (year: number) => void;
};

export default function MonthlySummary({ monthly, year, years, onYearChange }: Props) {
  const byMonth = new Map(monthly.filter((item) => item.year === year).map((item) => [item.month, item]));
  const months = Array.from({ length: 12 }, (_, index) => index + 1).map((month) => ({
    month,
    entry: byMonth.get(month),
  }));
  const maxDistance = Math.max(1, ...months.map((item) => item.entry?.distanceM ?? 0));

  return (
    <section className="rounded-3xl panel p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-stone-500">月度</p>
          <h2 className="text-2xl font-semibold text-stone-900">年度总结</h2>
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
      <div className="mt-5 space-y-2">
        {months.map((item) => {
          const distance = item.entry?.distanceM ?? 0;
          const percent = (distance / maxDistance) * 100;
          return (
            <div key={item.month} className="flex items-center gap-3 text-sm">
              <div className="w-10 text-stone-500">{formatMonthLabel(item.month)}</div>
              <div className="track relative h-2 flex-1 overflow-hidden rounded-full">
                <div
                  className="h-2 rounded-full bg-orange-400/80"
                  style={{ width: `${percent}%` }}
                />
              </div>
              <div className="w-20 text-right text-stone-600">
                {formatDistanceKm(distance, 1)}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
