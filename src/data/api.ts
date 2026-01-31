import type {
  Activity,
  CityStat,
  Daily,
  Distributions,
  Monthly,
  PersonalRecords,
  Summary,
} from "../types";

export type DataBundle = {
  activities: Activity[];
  daily: Daily[];
  summary: Summary;
  monthly: Monthly[];
  cityStats: CityStat[];
  distributions: Distributions;
  personalRecords: PersonalRecords | null;
};

const DATA_BASE = "/data";

async function loadJson<T>(file: string): Promise<T> {
  const response = await fetch(`${DATA_BASE}/${file}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load ${file}: ${response.status}`);
  }
  try {
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

async function loadOptionalJson<T>(file: string): Promise<T | null> {
  const response = await fetch(`${DATA_BASE}/${file}`, { cache: "no-store" });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Failed to load ${file}: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function loadData(): Promise<DataBundle> {
  const [summary, daily, monthly, cityStats, distributions, activities, personalRecords] =
    await Promise.all(
    [
      loadJson<Summary>("summary.json"),
      loadJson<Daily[]>("daily.json"),
      loadJson<Monthly[]>("monthly.json"),
      loadJson<CityStat[]>("city-stats.json"),
      loadJson<Distributions>("distributions.json"),
      loadJson<Activity[]>("activities.json"),
      loadOptionalJson<PersonalRecords>("personal-records.json"),
    ]
  );

  return {
    activities,
    daily,
    summary,
    monthly,
    cityStats,
    distributions,
    personalRecords,
  };
}
