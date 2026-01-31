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

const DIST_TOLERANCE = 0.05;

function getActivityTimeSeconds(activity: Activity): number | null {
  if (activity.durationS && activity.durationS > 0) {
    return activity.durationS;
  }
  if (
    activity.paceSecPerKm &&
    activity.paceSecPerKm > 0 &&
    activity.distanceM &&
    activity.distanceM > 0
  ) {
    return activity.paceSecPerKm * (activity.distanceM / 1000);
  }
  return null;
}

function isDistanceNear(distanceM: number | null, targetM: number): boolean {
  if (!distanceM || distanceM <= 0) {
    return false;
  }
  return Math.abs(distanceM - targetM) <= targetM * DIST_TOLERANCE;
}

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

function pickBestByTime(
  activities: Activity[],
  predicate: (activity: Activity) => boolean
): Activity | null {
  let best: Activity | null = null;
  let bestTime = Infinity;
  for (const activity of activities) {
    if (!predicate(activity)) {
      continue;
    }
    const time = getActivityTimeSeconds(activity);
    if (time === null || time <= 0) {
      continue;
    }
    if (time < bestTime) {
      best = activity;
      bestTime = time;
    }
  }
  return best;
}

export default function PersonalBests({ activities }: Props) {
  const best5kExact = pickBestByTime(
    activities,
    (activity) => isDistanceNear(activity.distanceM ?? null, 5000)
  );
  const best5k =
    best5kExact ??
    pickBestByTime(activities, (activity) => (activity.distanceM ?? 0) >= 5000);

  const best10kExact = pickBestByTime(
    activities,
    (activity) => isDistanceNear(activity.distanceM ?? null, 10000)
  );
  const best10k =
    best10kExact ??
    pickBestByTime(activities, (activity) => (activity.distanceM ?? 0) >= 10000);

  const longestDistance = pickBest(
    activities,
    (activity) => (activity.distanceM ?? 0) > 0,
    (next, current) => (next.distanceM ?? 0) > (current.distanceM ?? 0)
  );

  const best5kTime = best5k ? getActivityTimeSeconds(best5k) : null;
  const best10kTime = best10k ? getActivityTimeSeconds(best10k) : null;

  const items: BestItem[] = [
    {
      label: "最佳 5 公里",
      value: best5kTime ? formatDuration(best5kTime) : "--",
      date: best5k?.date ?? "--",
    },
    {
      label: "最佳 10 公里",
      value: best10kTime ? formatDuration(best10kTime) : "--",
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
      <h2 className="mt-2 text-2xl font-semibold text-stone-900">最佳成绩</h2>
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
