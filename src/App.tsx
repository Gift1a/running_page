import { useEffect, useMemo, useState } from "react";
import CityStats from "./components/CityStats";
import DistributionBars from "./components/DistributionBars";
import Heatmap from "./components/Heatmap";
import MonthlySummary from "./components/MonthlySummary";
import PersonalBests from "./components/PersonalBests";
import { loadData } from "./data/api";
import type { CityStat } from "./types";
import { formatDistanceKm, formatPace } from "./utils/format";

type StatCardProps = {
  label: string;
  value: string;
  subtext: string;
};

function StatCard({ label, value, subtext }: StatCardProps) {
  return (
    <div className="rounded-3xl panel p-6 shadow-sm">
      <p className="text-xs uppercase tracking-[0.3em] text-stone-500">{label}</p>
      <div className="mt-3 text-3xl font-semibold text-stone-900">{value}</div>
      <p className="mt-2 text-sm text-stone-500">{subtext}</p>
    </div>
  );
}

export default function App() {
  const [data, setData] = useState<Awaited<ReturnType<typeof loadData>> | null>(null);
  const [dataError, setDataError] = useState<string | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window === "undefined") {
      return "light";
    }
    const stored = window.localStorage.getItem("theme");
    if (stored === "light" || stored === "dark") {
      return stored;
    }
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  });
  const previewCities: CityStat[] = [
    { city: "Shanghai", country: "CN", admin1: null, runs: 2, distanceM: 12000, avgPaceSecPerKm: 340 },
    { city: "Beijing", country: "CN", admin1: null, runs: 1, distanceM: 11000, avgPaceSecPerKm: 360 },
    { city: "Shenzhen", country: "CN", admin1: null, runs: 2, distanceM: 9000, avgPaceSecPerKm: 370 },
    { city: "Guangzhou", country: "CN", admin1: null, runs: 1, distanceM: 8500, avgPaceSecPerKm: 365 },
    { city: "Chengdu", country: "CN", admin1: null, runs: 1, distanceM: 7000, avgPaceSecPerKm: 380 },
    { city: "Nanjing", country: "CN", admin1: null, runs: 1, distanceM: 6000, avgPaceSecPerKm: 355 },
    { city: "Suzhou", country: "CN", admin1: null, runs: 1, distanceM: 5000, avgPaceSecPerKm: 345 },
    { city: "Changsha", country: "CN", admin1: null, runs: 1, distanceM: 4500, avgPaceSecPerKm: 390 },
  ];
  const years = useMemo(() => {
    const set = new Set((data?.daily ?? []).map((entry) => Number(entry.date.slice(0, 4))));
    return Array.from(set).sort((a, b) => a - b);
  }, [data]);

  const monthlyYears = useMemo(() => {
    const set = new Set((data?.monthly ?? []).map((entry) => entry.year));
    return Array.from(set).sort((a, b) => a - b);
  }, [data]);

  const [heatmapYear, setHeatmapYear] = useState<number | null>(null);
  const [monthlyYear, setMonthlyYear] = useState<number | null>(null);
  const [distMode, setDistMode] = useState<"count" | "distance">("count");
  const [cityLimit, setCityLimit] = useState<number>(8);
  const cityStatsView = useMemo(() => {
    const stats = data?.cityStats ?? [];
    const base = stats.length >= 8 ? stats : [...stats, ...previewCities];
    return [...base].sort((a, b) => b.distanceM - a.distanceM);
  }, [data]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    let active = true;
    loadData()
      .then((payload) => {
        if (!active) {
          return;
        }
        setData(payload);
        setDataError(null);
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        setDataError(error instanceof Error ? error.message : String(error));
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!years.length) {
      return;
    }
    if (heatmapYear === null || !years.includes(heatmapYear)) {
      setHeatmapYear(years[years.length - 1]);
    }
  }, [years, heatmapYear]);

  useEffect(() => {
    if (!monthlyYears.length) {
      return;
    }
    if (monthlyYear === null || !monthlyYears.includes(monthlyYear)) {
      setMonthlyYear(monthlyYears[monthlyYears.length - 1]);
    }
  }, [monthlyYears, monthlyYear]);

  if (dataError) {
    return (
      <div className="min-h-screen">
        <header className="px-6 pt-8 pb-4 md:px-10">
          <div className="mx-auto max-w-6xl">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.4em] text-stone-500">Garmin 跑步</p>
                <h1 className="mt-2 text-4xl font-semibold text-stone-900 md:text-5xl">
                  跑步图谱
                </h1>
                <p className="mt-2 max-w-xl text-sm text-stone-500">
                  你的跑步故事速览，数据直接来自已解析的 FIT 记录。
                </p>
              </div>
              <button
                className="chip rounded-full px-3 py-2 text-xs text-stone-600"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                type="button"
              >
                {theme === "dark" ? "夜间模式" : "日间模式"}
              </button>
            </div>
          </div>
        </header>
        <main className="px-6 pb-12 md:px-10">
          <div className="mx-auto max-w-6xl">
            <div className="rounded-3xl panel p-6 shadow-sm text-sm text-stone-600">
              数据加载失败：{dataError}
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen">
        <header className="px-6 pt-8 pb-4 md:px-10">
          <div className="mx-auto max-w-6xl">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.4em] text-stone-500">Garmin 跑步</p>
                <h1 className="mt-2 text-4xl font-semibold text-stone-900 md:text-5xl">
                  跑步图谱
                </h1>
                <p className="mt-2 max-w-xl text-sm text-stone-500">
                  你的跑步故事速览，数据直接来自已解析的 FIT 记录。
                </p>
              </div>
              <button
                className="chip rounded-full px-3 py-2 text-xs text-stone-600"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                type="button"
              >
                {theme === "dark" ? "夜间模式" : "日间模式"}
              </button>
            </div>
          </div>
        </header>
        <main className="px-6 pb-12 md:px-10">
          <div className="mx-auto max-w-6xl">
            <div className="rounded-3xl panel p-6 shadow-sm text-sm text-stone-600">
              数据加载中...
            </div>
          </div>
        </main>
      </div>
    );
  }

  const paceLabel = (start: number, end: number) => {
    const startLabel = formatPace(start).replace("/km", "");
    const endLabel = formatPace(end).replace("/km", "");
    return `${startLabel}-${endLabel}`;
  };

  const hrLabel = (start: number, end: number) => `${start}-${end} 次/分`;
  const distLabel = (start: number, end: number) =>
    `${(start / 1000).toFixed(1)}-${(end / 1000).toFixed(1)} km`;

  return (
    <div className="min-h-screen">
      <header className="px-6 pt-8 pb-4 md:px-10">
        <div className="mx-auto max-w-6xl">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.4em] text-stone-500">Garmin 跑步</p>
              <h1 className="mt-2 text-4xl font-semibold text-stone-900 md:text-5xl">
                跑步图谱
              </h1>
              <p className="mt-2 max-w-xl text-sm text-stone-500">
                你的跑步故事速览，数据直接来自已解析的 FIT 记录。
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                className="chip rounded-full px-3 py-2 text-xs text-stone-600"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                type="button"
              >
                {theme === "dark" ? "夜间模式" : "日间模式"}
              </button>
              <div className="chip rounded-full px-4 py-2 text-xs text-stone-600">
                {data.summary.totalDays} 天有跑步
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="px-6 pb-12 md:px-10">
        <div className="mx-auto max-w-6xl">
        <section className="mt-6 grid gap-6 lg:grid-cols-3">
          <StatCard
            label="跑步天数"
            value={`${data.summary.totalDays}`}
            subtext="至少有一次跑步的天数"
          />
          <StatCard
            label="总距离"
            value={formatDistanceKm(data.summary.totalDistanceM, 1)}
            subtext="累计跑步里程"
          />
          <StatCard
            label="平均距离"
            value={formatDistanceKm(data.summary.avgDistancePerDayM, 1)}
            subtext="每个跑步日平均里程"
          />
        </section>

        <section className="mt-8">
          {heatmapYear === null ? (
            <div className="rounded-3xl panel p-6 shadow-sm text-sm text-stone-600">
              热力图加载中...
            </div>
          ) : (
            <Heatmap
              daily={data.daily}
              year={heatmapYear}
              years={years}
              onYearChange={setHeatmapYear}
            />
          )}
        </section>

        <section className="mt-8 rounded-3xl panel p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-stone-500">分布</p>
              <h2 className="text-2xl font-semibold text-stone-900">跑步数据分布</h2>
            </div>
            <div className="chip flex items-center gap-2 rounded-full p-1 text-xs">
              <button
                className={`rounded-full px-3 py-1 ${
                  distMode === "count" ? "bg-stone-900 text-white" : "text-stone-600"
                }`}
                onClick={() => setDistMode("count")}
              >
                按次数
              </button>
              <button
                className={`rounded-full px-3 py-1 ${
                  distMode === "distance" ? "bg-stone-900 text-white" : "text-stone-600"
                }`}
                onClick={() => setDistMode("distance")}
              >
                按距离
              </button>
            </div>
          </div>
          <div className="mt-6 grid gap-6 lg:grid-cols-[1.1fr,1fr]">
            <div className="space-y-6">
            <DistributionBars
              title="配速"
              distribution={data.distributions.paceSecPerKm}
              mode={distMode}
              formatLabel={paceLabel}
            />
            <DistributionBars
              title="心率"
              distribution={data.distributions.avgHr}
              mode={distMode}
              formatLabel={hrLabel}
            />
            </div>
            <DistributionBars
              title="距离"
              distribution={data.distributions.distanceM}
              mode={distMode}
              formatLabel={distLabel}
            />
          </div>
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[1fr,1fr]">
          <CityStats
            stats={cityStatsView}
            limit={cityLimit}
            options={[4, 8, 12]}
            onLimitChange={setCityLimit}
          />
          <MonthlySummary
            monthly={data.monthly}
            year={monthlyYear ?? new Date().getFullYear()}
            years={monthlyYears}
            onYearChange={setMonthlyYear}
          />
        </section>

        <section className="mt-8">
          <PersonalBests activities={data.activities} />
        </section>
        </div>
      </main>
    </div>
  );
}
