import type { Activity } from "../types";
import { formatDistanceKm, formatDuration } from "../utils/format";

type Props = {
  activities: Activity[];
};

type BestItem = {
  label: string;
  value: string;
  date: string;
};

function pickBest(
  activities: Activity[],
  predicate: (activity: Activity) => boolean,
  better: (next: Activity, current: Activity) => boolean
): Activity | null {
  let best: Activity | null = null;
  for (const activity of activities) {
    if (!predicate(activity)) {
      continue;
    }
    if (!best || better(activity, best)) {
      best = activity;
    }
  }
  return best;
}

export default function PersonalBests({ activities }: Props) {
  const best5k = pickBest(
    activities,
    (activity) => (activity.paceSecPerKm ?? 0) > 0 && (activity.distanceM ?? 0) >= 5000,
    (next, current) => (next.paceSecPerKm ?? Infinity) < (current.paceSecPerKm ?? Infinity)
  );
  const best10k = pickBest(
    activities,
    (activity) => (activity.paceSecPerKm ?? 0) > 0 && (activity.distanceM ?? 0) >= 10000,
    (next, current) => (next.paceSecPerKm ?? Infinity) < (current.paceSecPerKm ?? Infinity)
  );
  const longestDistance = pickBest(
    activities,
    (activity) => (activity.distanceM ?? 0) > 0,
    (next, current) => (next.distanceM ?? 0) > (current.distanceM ?? 0)
  );

  const items: BestItem[] = [
    {
      label: "最佳 5 公里",
      value: best5k ? formatDuration((best5k.paceSecPerKm ?? 0) * 5) : "--",
      date: best5k?.date ?? "--",
    },
    {
      label: "最佳 10 公里",
      value: best10k ? formatDuration((best10k.paceSecPerKm ?? 0) * 10) : "--",
      date: best10k?.date ?? "--",
    },
    {
      label: "最长距离",
      value: longestDistance ? formatDistanceKm(longestDistance.distanceM, 1) : "--",
      date: longestDistance?.date ?? "--",
    },
  ];

  return (
    <section className="rounded-3xl panel p-6 shadow-sm">
      <p className="text-xs uppercase tracking-[0.3em] text-stone-500">个人最佳</p>
      <h2 className="mt-2 text-2xl font-semibold text-stone-900">最好成绩</h2>
      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <div key={item.label} className="panel-inner rounded-2xl p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-stone-500">{item.label}</p>
            <div className="mt-2 text-lg font-semibold text-stone-900">{item.value}</div>
            <div className="mt-1 text-xs text-stone-500">{item.date}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
