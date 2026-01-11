export function formatDistanceKm(value?: number | null, digits = 2): string {
  if (!value || value <= 0) {
    return "0.00 km";
  }
  return `${(value / 1000).toFixed(digits)} km`;
}

export function formatDuration(value?: number | null): string {
  if (!value || value <= 0) {
    return "--";
  }
  const total = Math.round(value);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

export function formatPace(value?: number | null): string {
  if (!value || value <= 0 || !Number.isFinite(value)) {
    return "--";
  }
  const total = Math.round(value);
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}/km`;
}

export function formatNumber(value?: number | null, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "--";
  }
  return value.toFixed(digits);
}

export function formatShortDate(value: string): string {
  const [year, month, day] = value.split("-");
  return `${year}-${month}-${day}`;
}

export function formatMonthLabel(month: number): string {
  return `${month}月`;
}
