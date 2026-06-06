'use client';

import { useState } from 'react';
import { PriceStats } from '@/lib/types';

const fmt = (n: number) => '$' + Math.round(n).toLocaleString();

interface Props {
  stats: PriceStats;
  query: string;
  onSpendChange?: (spend: number) => void;
}

export default function SavingsCalculator({ stats, query, onSpendChange }: Props) {
  const [raw, setRaw] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [contact, setContact] = useState({ name: '', email: '', company: '' });

  const spend = parseFloat(raw.replace(/[^0-9.]/g, '')) || 0;

  const range = stats.max - stats.min || 1;
  const pctile = spend <= stats.min ? 0 : spend >= stats.max ? 100 : Math.round(((spend - stats.min) / range) * 100);
  const isHigh = spend > 0 && spend > stats.p25;
  const savings = isHigh ? Math.max(0, spend - stats.p25) : 0;
  const fee = savings * 0.01;
  const net = savings - fee;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="bg-gradient-to-br from-blue-800 to-blue-600 px-6 py-5 text-white">
        <h3 className="font-bold text-lg">Calculate Your Savings</h3>
        <p className="text-blue-200 text-sm mt-1">How much do you spend on {query}?</p>
      </div>

      <div className="p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Annual spend on this item</label>
          <div className="relative">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">$</span>
            <input
              type="text"
              value={raw}
              onChange={(e) => {
                setRaw(e.target.value);
                const v = parseFloat(e.target.value.replace(/[^0-9.]/g, '')) || 0;
                onSpendChange?.(v);
              }}
              placeholder="e.g. 85,000"
              className="w-full pl-8 pr-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
            />
          </div>
        </div>

        {spend > 0 && (
          <div className="space-y-4">
            {/* Position indicator */}
            <div>
              <div className="flex justify-between text-xs text-gray-400 mb-2">
                <span>Lowest payers</span>
                <span>Highest payers</span>
              </div>
              <div className="relative h-3 bg-gradient-to-r from-emerald-400 via-yellow-400 to-red-500 rounded-full">
                <div
                  className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white border-2 border-gray-900 rounded-full shadow-md transition-all duration-300"
                  style={{ left: `calc(${Math.min(pctile, 94)}% )` }}
                />
              </div>
              <p className="text-xs text-center text-gray-500 mt-2">
                {isHigh
                  ? `You're in the top ${100 - pctile}% of payers — likely overpaying`
                  : 'You appear to be getting a competitive price'}
              </p>
            </div>

            {/* Savings box */}
            {isHigh && (
              <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4">
                <p className="text-sm font-semibold text-emerald-800 mb-1">Estimated annual savings</p>
                <p className="text-3xl font-black text-emerald-600 mb-3">{fmt(savings)}</p>
                <div className="border-t border-emerald-100 pt-3 space-y-1 text-xs text-emerald-700">
                  <div className="flex justify-between">
                    <span>Gross savings</span>
                    <span>{fmt(savings)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>ProcureEdge fee (1%)</span>
                    <span>−{fmt(fee)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-emerald-900 border-t border-emerald-200 pt-1 mt-1">
                    <span>You keep</span>
                    <span>{fmt(net)}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Benchmark */}
            <div className="bg-gray-50 rounded-xl p-4 text-sm">
              <p className="font-medium text-gray-800 mb-2">Market benchmarks</p>
              <div className="space-y-1 text-gray-600">
                <div className="flex justify-between">
                  <span>Best rate seen</span>
                  <span className="text-emerald-600 font-medium">{fmt(stats.min)}</span>
                </div>
                <div className="flex justify-between">
                  <span>25th percentile</span>
                  <span className="text-blue-600 font-medium">{fmt(stats.p25)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Median</span>
                  <span className="font-medium">{fmt(stats.median)}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* CTA */}
        {!submitted && (
          <>
            {!showForm ? (
              <button
                onClick={() => setShowForm(true)}
                disabled={!isHigh}
                className="w-full py-4 bg-emerald-500 hover:bg-emerald-600 disabled:bg-gray-100 disabled:text-gray-300 text-white font-semibold rounded-xl transition-colors"
              >
                {spend === 0
                  ? 'Enter your spend above'
                  : isHigh
                  ? 'Find me a better supplier →'
                  : "You're already competitive"}
              </button>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-3">
                <input
                  required
                  type="text"
                  placeholder="Your name"
                  value={contact.name}
                  onChange={(e) => setContact((c) => ({ ...c, name: e.target.value }))}
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                />
                <input
                  required
                  type="email"
                  placeholder="Work email"
                  value={contact.email}
                  onChange={(e) => setContact((c) => ({ ...c, email: e.target.value }))}
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                />
                <input
                  required
                  type="text"
                  placeholder="Company name"
                  value={contact.company}
                  onChange={(e) => setContact((c) => ({ ...c, company: e.target.value }))}
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                />
                <button
                  type="submit"
                  className="w-full py-3 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold rounded-xl transition-colors"
                >
                  Connect me — save {fmt(net)}/yr
                </button>
                <p className="text-xs text-gray-400 text-center">
                  No payment until we save you money. 1% of verified savings only.
                </p>
              </form>
            )}
          </>
        )}

        {submitted && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 text-center">
            <div className="text-3xl mb-2">✓</div>
            <p className="font-semibold text-emerald-800">We&apos;re on it, {contact.name}!</p>
            <p className="text-sm text-emerald-600 mt-1">
              Expect an email at {contact.email} within 24 hours with vetted supplier options.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
