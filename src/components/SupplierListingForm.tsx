'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
  'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
  'VA','WA','WV','WI','WY',
];

const CATEGORY_OPTIONS = [
  'Fasteners', 'Hardware', 'Hydraulics', 'Pneumatics', 'Valves', 'Safety / PPE',
  'Cutting Tools', 'Abrasives', 'Bearings', 'Seals & Gaskets', 'Electrical',
  'MRO / General', 'Power Transmission', 'Fluid Control', 'Structural',
];

export default function SupplierListingForm() {
  const router = useRouter();
  const [step, setStep] = useState<'form' | 'pay' | 'done'>('form');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    company: '',
    contact: '',
    email: '',
    phone: '',
    description: '',
    categories: [] as string[],
    price_min: '',
    price_max: '',
    state: '',
  });

  const set = (k: keyof typeof form, v: string | string[]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const toggleCategory = (cat: string) => {
    set(
      'categories',
      form.categories.includes(cat)
        ? form.categories.filter((c) => c !== cat)
        : [...form.categories, cat],
    );
  };

  const submitForm = (e: React.FormEvent) => {
    e.preventDefault();
    if (form.categories.length === 0) {
      setError('Select at least one product category.');
      return;
    }
    setError('');
    setStep('pay');
  };

  const submitPayment = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/suppliers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          price_min: form.price_min ? parseFloat(form.price_min.replace(/,/g, '')) : null,
          price_max: form.price_max ? parseFloat(form.price_max.replace(/,/g, '')) : null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Submission failed');
      setStep('done');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (step === 'done') {
    return (
      <div className="text-center py-16">
        <div className="text-5xl mb-4">✓</div>
        <h2 className="text-2xl font-bold text-gray-900 mb-3">Listing is live!</h2>
        <p className="text-gray-500 mb-2">
          <strong>{form.company}</strong> is now visible to buyers searching for your products.
        </p>
        <p className="text-gray-400 text-sm mb-8">
          You&apos;ll receive email introductions when we match you with a qualified buyer.
        </p>
        <button
          onClick={() => router.push('/')}
          className="px-6 py-3 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded-xl transition-colors"
        >
          Back to home
        </button>
      </div>
    );
  }

  if (step === 'pay') {
    return (
      <div className="max-w-md mx-auto">
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
          <div className="bg-gradient-to-br from-blue-800 to-blue-600 px-6 py-5 text-white">
            <h3 className="font-bold text-lg">Publish your listing — $1</h3>
            <p className="text-blue-200 text-sm mt-1">One-time fee. Listed for 12 months.</p>
          </div>
          <div className="p-6 space-y-4">
            {/* Summary */}
            <div className="bg-gray-50 rounded-xl p-4 text-sm space-y-1">
              <div className="flex justify-between text-gray-600">
                <span>Company</span>
                <span className="font-medium text-gray-900">{form.company}</span>
              </div>
              <div className="flex justify-between text-gray-600">
                <span>Categories</span>
                <span className="font-medium text-gray-900 text-right max-w-40 truncate">
                  {form.categories.join(', ')}
                </span>
              </div>
              <div className="flex justify-between text-gray-600 border-t border-gray-200 pt-2 mt-2">
                <span className="font-semibold text-gray-800">Listing fee</span>
                <span className="font-bold text-emerald-600">$1.00</span>
              </div>
            </div>

            {/* Mock card */}
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Card number</label>
                <input
                  type="text"
                  placeholder="4242 4242 4242 4242"
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Expiry</label>
                  <input
                    type="text"
                    placeholder="MM / YY"
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">CVC</label>
                  <input
                    type="text"
                    placeholder="123"
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            <p className="text-xs text-amber-600 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
              Beta mode: listings are activated instantly. Real Stripe integration coming soon — no charge yet.
            </p>

            {error && <p className="text-red-500 text-sm">{error}</p>}

            <button
              onClick={submitPayment}
              disabled={loading}
              className="w-full py-4 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-bold rounded-xl transition-colors"
            >
              {loading ? 'Publishing…' : 'Pay $1 and publish listing →'}
            </button>
            <button
              onClick={() => setStep('form')}
              className="w-full py-2 text-sm text-gray-400 hover:text-gray-600 transition-colors"
            >
              ← Edit listing
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={submitForm} className="space-y-6 max-w-2xl">
      {/* Company info */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
        <h3 className="font-semibold text-gray-900">Company information</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Company name *</label>
            <input
              required
              value={form.company}
              onChange={(e) => set('company', e.target.value)}
              placeholder="Acme Industrial Supply"
              className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Contact name *</label>
            <input
              required
              value={form.contact}
              onChange={(e) => set('contact', e.target.value)}
              placeholder="Jane Smith"
              className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Work email *</label>
            <input
              required
              type="email"
              value={form.email}
              onChange={(e) => set('email', e.target.value)}
              placeholder="jane@acmesupply.com"
              className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Phone</label>
            <input
              type="tel"
              value={form.phone}
              onChange={(e) => set('phone', e.target.value)}
              placeholder="555-000-1234"
              className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-1">State</label>
          <select
            value={form.state}
            onChange={(e) => set('state', e.target.value)}
            className="w-40 px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">Select…</option>
            {US_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {/* What you supply */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
        <h3 className="font-semibold text-gray-900">What do you supply?</h3>
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-1">
            Description * <span className="text-gray-400 font-normal">(be specific — buyers search by keyword)</span>
          </label>
          <textarea
            required
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            rows={4}
            placeholder="e.g. Full-line distributor of industrial fasteners: hex bolts, cap screws, nuts, washers, rivets. All grades including grade 8 steel, stainless, and titanium. Volume pricing available."
            className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">Product categories *</label>
          <div className="flex flex-wrap gap-2">
            {CATEGORY_OPTIONS.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => toggleCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                  form.categories.includes(cat)
                    ? 'bg-blue-700 text-white border-blue-700'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-blue-400'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Min deal size / yr</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">$</span>
              <input
                type="text"
                value={form.price_min}
                onChange={(e) => set('price_min', e.target.value)}
                placeholder="5,000"
                className="w-full pl-8 pr-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Max deal size / yr</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">$</span>
              <input
                type="text"
                value={form.price_max}
                onChange={(e) => set('price_max', e.target.value)}
                placeholder="1,000,000"
                className="w-full pl-8 pr-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      <button
        type="submit"
        className="w-full py-4 bg-blue-700 hover:bg-blue-800 text-white font-bold rounded-xl transition-colors"
      >
        Continue to payment — $1 →
      </button>
      <p className="text-xs text-gray-400 text-center">
        Listed for 12 months. We only send introductions when we have a qualified buyer match.
      </p>
    </form>
  );
}
