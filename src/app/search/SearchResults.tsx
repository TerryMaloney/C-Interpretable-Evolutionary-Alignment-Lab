'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import SearchBar from '@/components/SearchBar';
import PriceInsights from '@/components/PriceInsights';
import SavingsCalculator from '@/components/SavingsCalculator';
import { PriceAnalysis } from '@/lib/types';

const fmtAmt = (n: number) =>
  n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M` : `$${Math.round(n / 1000)}K`;

export default function SearchResults() {
  const params = useSearchParams();
  const q = params.get('q') ?? '';

  const [data, setData] = useState<PriceAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!q) return;
    setLoading(true);
    setError('');
    setData(null);

    fetch(`/api/search?q=${encodeURIComponent(q)}`)
      .then((r) => r.json())
      .then((d: PriceAnalysis & { error?: string }) => {
        if (d.error) setError(d.error);
        else setData(d);
      })
      .catch(() => setError('Failed to load. Please try again.'))
      .finally(() => setLoading(false));
  }, [q]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="bg-white border-b border-gray-200 px-8 py-4 flex items-center gap-6">
        <Link href="/" className="font-bold text-xl text-blue-900 tracking-tight shrink-0">
          ProcureEdge
        </Link>
        <div className="flex-1 max-w-xl">
          <SearchBar defaultValue={q} />
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-8 py-10">
        {/* Loading */}
        {loading && (
          <div className="text-center py-32">
            <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-400">Analyzing procurement contracts for &quot;{q}&quot;…</p>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="text-center py-32 text-red-500">
            {error}
          </div>
        )}

        {/* Results */}
        {data && !loading && (
          <div className="grid grid-cols-3 gap-8 items-start">
            <div className="col-span-2 space-y-6">
              {/* Header */}
              <div>
                <h1 className="text-2xl font-bold text-gray-900 capitalize">
                  Price Intelligence: {q}
                </h1>
                <p className="text-gray-400 mt-1 text-sm">
                  Based on {data.totalContracts.toLocaleString()} federal contracts (2023–2025) ·{' '}
                  <span className="text-blue-500">Source: USASpending.gov</span>
                </p>
              </div>

              <PriceInsights data={data} />

              {/* Contract table */}
              <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 flex items-baseline justify-between">
                  <h3 className="font-semibold text-gray-900">Recent Contracts</h3>
                  <span className="text-xs text-gray-400">Top 10 by value</span>
                </div>
                <div className="divide-y divide-gray-50">
                  {data.contracts.slice(0, 10).map((c) => (
                    <div key={c.id} className="px-6 py-4 flex items-start justify-between gap-4 hover:bg-gray-50 transition-colors">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-800 truncate">{c.recipientName}</p>
                        <p className="text-xs text-gray-400 truncate mt-0.5">
                          {c.description || 'No description available'}
                        </p>
                        <p className="text-xs text-gray-300 mt-0.5">{c.agencyName}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-sm font-semibold text-gray-900">
                          {fmtAmt(c.awardAmount)}
                        </p>
                        {c.periodDays !== 365 && (
                          <p className="text-xs text-gray-400">
                            {Math.round(c.periodDays / 30)}mo contract
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <p className="text-xs text-gray-300 px-1">
                All data is public record sourced from USASpending.gov. Contract values are annualized for comparison.
              </p>
            </div>

            {/* Sidebar */}
            <div className="col-span-1 sticky top-6">
              <SavingsCalculator stats={data.stats} query={q} />
            </div>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && !data && q && (
          <div className="text-center py-32 text-gray-400">
            No contracts found for &quot;{q}&quot;. Try a broader term.
          </div>
        )}
      </div>
    </div>
  );
}
