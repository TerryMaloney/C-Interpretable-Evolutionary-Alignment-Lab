'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import SearchBar from '@/components/SearchBar';
import PriceInsights from '@/components/PriceInsights';
import SavingsCalculator from '@/components/SavingsCalculator';
import MatchedSuppliers from '@/components/MatchedSuppliers';
import { PriceAnalysis } from '@/lib/types';
import { MatchedSupplier } from '@/lib/matching';

const fmtAmt = (n: number) =>
  n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M` : `$${Math.round(n / 1000)}K`;

export default function SearchResults() {
  const params = useSearchParams();
  const q = params.get('q') ?? '';

  const [data, setData] = useState<PriceAnalysis | null>(null);
  const [suppliers, setSuppliers] = useState<MatchedSupplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [annualSpend, setAnnualSpend] = useState<number>(0);

  // Fetch USASpending market data
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
      .catch(() => setError('Failed to load market data. Please try again.'))
      .finally(() => setLoading(false));
  }, [q]);

  // Fetch supplier matches — re-runs when spend changes so results refine
  const fetchMatches = useCallback(
    (spend: number) => {
      if (!q) return;
      const url = `/api/match?q=${encodeURIComponent(q)}${spend > 0 ? `&spend=${spend}` : ''}`;
      fetch(url)
        .then((r) => r.json())
        .then((d: { matches: MatchedSupplier[] }) => setSuppliers(d.matches ?? []))
        .catch(() => {});
    },
    [q],
  );

  useEffect(() => { fetchMatches(0); }, [fetchMatches]);

  // When buyer enters spend in the calculator, refetch matches with price context
  const handleSpendChange = useCallback(
    (spend: number) => {
      setAnnualSpend(spend);
      fetchMatches(spend);
    },
    [fetchMatches],
  );

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
        <Link
          href="/suppliers/new"
          className="shrink-0 text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors"
        >
          List your business →
        </Link>
      </nav>

      <div className="max-w-6xl mx-auto px-8 py-10">
        {/* Loading */}
        {loading && (
          <div className="text-center py-32">
            <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-400">Analyzing procurement contracts for &ldquo;{q}&rdquo;…</p>
          </div>
        )}

        {error && !loading && (
          <div className="text-center py-32 text-red-500">{error}</div>
        )}

        {data && !loading && (
          <div className="grid grid-cols-3 gap-8 items-start">
            {/* Main column */}
            <div className="col-span-2 space-y-6">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 capitalize">
                  Price Intelligence: {q}
                </h1>
                <p className="text-gray-400 mt-1 text-sm">
                  {data.totalContracts.toLocaleString()} federal contracts (2023–2025) ·{' '}
                  <a
                    href="https://usaspending.gov"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-500 hover:underline"
                  >
                    USASpending.gov
                  </a>
                </p>
              </div>

              <PriceInsights data={data} />

              {/* Matched suppliers */}
              <MatchedSuppliers suppliers={suppliers} query={q} />

              {/* Contract table */}
              <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 flex items-baseline justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900">Federal Contract Records</h3>
                    <p className="text-xs text-gray-400 mt-0.5">What others paid — raw public data</p>
                  </div>
                  <span className="text-xs text-gray-400">Top 10 by value</span>
                </div>
                <div className="divide-y divide-gray-50">
                  {data.contracts.slice(0, 10).map((c) => (
                    <div
                      key={c.id}
                      className="px-6 py-4 flex items-start justify-between gap-4 hover:bg-gray-50 transition-colors"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-800 truncate">{c.recipientName}</p>
                        <p className="text-xs text-gray-400 truncate mt-0.5">
                          {c.description || 'No description available'}
                        </p>
                        <p className="text-xs text-gray-300 mt-0.5">{c.agencyName}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-sm font-semibold text-gray-900">{fmtAmt(c.awardAmount)}</p>
                        {c.periodDays !== 365 && (
                          <p className="text-xs text-gray-400">{Math.round(c.periodDays / 30)}mo</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <p className="text-xs text-gray-300 px-1">
                All data is public record sourced from USASpending.gov. Contract values are annualized for comparison. Federal contract prices may differ from commercial market rates.
              </p>
            </div>

            {/* Sidebar */}
            <div className="col-span-1 sticky top-6 space-y-4">
              <SavingsCalculator
                stats={data.stats}
                query={q}
                onSpendChange={handleSpendChange}
              />
              {annualSpend > 0 && suppliers.length > 0 && (
                <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 text-xs text-blue-700">
                  Supplier matches updated for your ${annualSpend.toLocaleString()} spend level.
                </div>
              )}
            </div>
          </div>
        )}

        {!loading && !error && !data && q && (
          <div className="text-center py-32 text-gray-400">
            No contracts found for &ldquo;{q}&rdquo;. Try a broader search term.
          </div>
        )}
      </div>
    </div>
  );
}
