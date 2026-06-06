import { PriceAnalysis } from '@/lib/types';

const fmt = (n: number) =>
  n >= 1_000_000
    ? `$${(n / 1_000_000).toFixed(1)}M`
    : n >= 1_000
    ? `$${Math.round(n / 1000)}K`
    : `$${Math.round(n)}`;

const fmtFull = (n: number) => '$' + Math.round(n).toLocaleString();

interface Props {
  data: PriceAnalysis;
}

const BUCKETS = [
  { label: '<$10K', min: 0, max: 10_000 },
  { label: '$10K–50K', min: 10_000, max: 50_000 },
  { label: '$50K–250K', min: 50_000, max: 250_000 },
  { label: '$250K–1M', min: 250_000, max: 1_000_000 },
  { label: '>$1M', min: 1_000_000, max: Infinity },
];

export default function PriceInsights({ data }: Props) {
  const { stats, contracts } = data;

  const buckets = BUCKETS.map((b) => ({
    ...b,
    count: contracts.filter((c) => c.annualizedAmount >= b.min && c.annualizedAmount < b.max).length,
  }));
  const maxCount = Math.max(...buckets.map((b) => b.count), 1);

  const statCards = [
    { label: 'Best rate seen', value: fmtFull(stats.min), color: 'text-emerald-600' },
    { label: '25th percentile', value: fmtFull(stats.p25), color: 'text-blue-500' },
    { label: 'Median', value: fmtFull(stats.median), color: 'text-blue-800' },
    { label: 'Highest paid', value: fmtFull(stats.max), color: 'text-red-500' },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        {statCards.map((s) => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-400 mb-1">{s.label}</p>
            <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-gray-300 mt-1">annualized</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-1">Contract value distribution</h3>
        <p className="text-xs text-gray-400 mb-5">Annualized, top 100 contracts by value</p>
        <div className="space-y-3">
          {buckets.map((b) => (
            <div key={b.label} className="flex items-center gap-4">
              <div className="w-28 text-sm text-gray-500 text-right shrink-0">{b.label}</div>
              <div className="flex-1 bg-gray-100 rounded-full h-7 overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all duration-700"
                  style={{ width: `${(b.count / maxCount) * 100}%` }}
                />
              </div>
              <div className="w-6 text-sm text-gray-400 shrink-0 text-right">{b.count}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
