export type Activity = {
  id: string;
  sourceFile: string;
  sport: string;
  startTime: string;
  startTimeUtc?: string;
  date: string;
  distanceM: number | null;
  durationS: number | null;
  paceSecPerKm: number | null;
  avgHr: number | null;
  lat: number | null;
  lon: number | null;
  city: string;
  country: string | null;
  admin1: string | null;
};

export type DailyActivity = {
  id: string;
  startTime: string;
  startTimeUtc?: string;
  distanceM: number | null;
  durationS: number | null;
  paceSecPerKm: number | null;
  avgHr: number | null;
};

export type Daily = {
  date: string;
  distanceM: number;
  durationS: number;
  activities: DailyActivity[];
};

export type Summary = {
  totalDays: number;
  totalDistanceM: number;
  avgDistancePerDayM: number;
};

export type Monthly = {
  year: number;
  month: number;
  distanceM: number;
  durationS: number;
  days: number;
};

export type CityStat = {
  city: string;
  country: string | null;
  admin1: string | null;
  runs: number;
  distanceM: number;
  avgPaceSecPerKm: number | null;
};

export type DistributionBin = {
  start: number;
  end: number;
  count: number;
  distanceM: number;
};

export type Distribution = {
  binSize: number;
  bins: DistributionBin[];
};

export type Distributions = {
  paceSecPerKm: Distribution;
  avgHr: Distribution;
  distanceM: Distribution;
};
