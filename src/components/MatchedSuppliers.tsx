import { MatchedSupplier } from '@/lib/matching';

interface Props {
  suppliers: MatchedSupplier[];
  query: string;
}

const SCORE_COLOR = (s: number) =>
  s >= 70 ? 'text-emerald-600 bg-emerald-50 border-emerald-200' :
  s >= 40 ? 'text-blue-600 bg-blue-50 border-blue-200' :
             'text-gray-500 bg-gray-50 border-gray-200';

const fmtRange = (min: number | null, max: number | null) => {
  if (!min && !max) return null;
  const fmtN = (n: number) => n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M` : `$${Math.round(n / 1000)}K`;
  if (min && max) return `${fmtN(min)} – ${fmtN(max)}/yr`;
  if (min) return `${fmtN(min)}+/yr`;
  return `up to ${fmtN(max!)}/yr`;
};

export default function MatchedSuppliers({ suppliers, query }: Props) {
  if (suppliers.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-6 text-center text-gray-400 text-sm">
        No supplier matches yet for &ldquo;{query}&rdquo;.{' '}
        <a href="/suppliers/new" className="text-blue-600 hover:underline">
          List your business →
        </a>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 flex items-baseline justify-between">
        <h3 className="font-semibold text-gray-900">Matched Suppliers</h3>
        <span className="text-xs text-gray-400">{suppliers.length} found · ranked by relevance</span>
      </div>

      <div className="divide-y divide-gray-50">
        {suppliers.map((s) => (
          <div key={s.id} className="px-6 py-5 hover:bg-gray-50 transition-colors">
            <div className="flex items-start justify-between gap-4 mb-2">
              <div>
                <p className="font-semibold text-gray-900">{s.company}</p>
                {s.state && (
                  <p className="text-xs text-gray-400 mt-0.5">{s.state}</p>
                )}
              </div>
              <div className={`shrink-0 px-2.5 py-1 rounded-lg border text-xs font-bold ${SCORE_COLOR(s.score)}`}>
                {s.score}% match
              </div>
            </div>

            <p className="text-sm text-gray-600 leading-relaxed mb-3 line-clamp-2">
              {s.description}
            </p>

            <div className="flex flex-wrap gap-1.5 mb-3">
              {s.categories.map((cat) => (
                <span key={cat} className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">
                  {cat}
                </span>
              ))}
              {s.state && (
                <span className="px-2 py-0.5 bg-blue-50 text-blue-500 rounded text-xs">
                  {s.state}
                </span>
              )}
            </div>

            {/* Match reasons */}
            <div className="flex flex-wrap gap-2 mb-3">
              {s.matchReasons.map((r) => (
                <span key={r} className="text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                  ✓ {r}
                </span>
              ))}
            </div>

            {/* Deal size + score breakdown */}
            <div className="flex items-center justify-between text-xs text-gray-400">
              {fmtRange(s.price_min, s.price_max) && (
                <span>Deal range: {fmtRange(s.price_min, s.price_max)}</span>
              )}
              <div className="flex gap-3 ml-auto text-right">
                {s.scoreBreakdown.pscMatch > 0 && (
                  <span>Category: +{s.scoreBreakdown.pscMatch}</span>
                )}
                {s.scoreBreakdown.keywordMatch > 0 && (
                  <span>Keywords: +{s.scoreBreakdown.keywordMatch}</span>
                )}
                {s.scoreBreakdown.priceCompatibility > 0 && (
                  <span>Price fit: +{s.scoreBreakdown.priceCompatibility}</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
        <a
          href="/suppliers/new"
          className="text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors"
        >
          Are you a supplier? List your business for $1 →
        </a>
      </div>
    </div>
  );
}
