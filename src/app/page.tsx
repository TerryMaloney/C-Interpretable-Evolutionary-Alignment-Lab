import SearchBar from '@/components/SearchBar';

const EXAMPLES = ['steel fasteners', 'hydraulic fittings', 'industrial valves', 'safety gloves', 'cutting tools'];

const STATS = [
  { value: '$847B+', label: 'Procurement data analyzed' },
  { value: '23%', label: 'Average buyer savings' },
  { value: '1%', label: 'Our fee — on savings only' },
];

const STEPS = [
  {
    n: '01',
    title: 'Search your product',
    body: 'Enter any industrial supply. We pull real contract prices from federal procurement records — public data, updated continuously.',
  },
  {
    n: '02',
    title: 'See the price gap',
    body: "Instantly see what others actually paid. Enter your current spend and we'll show you exactly where you stand.",
  },
  {
    n: '03',
    title: 'Connect. Save. Pay nothing upfront.',
    body: "We match you with better suppliers. If you save money, we keep 1% of the savings. If you don't save, you pay nothing.",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white font-sans">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-4 border-b border-gray-100">
        <span className="font-bold text-xl text-blue-900 tracking-tight">ProcureEdge</span>
        <div className="flex gap-6 text-sm text-gray-500">
          <a href="#how" className="hover:text-gray-900 transition-colors">How it works</a>
          <a href="#faq" className="hover:text-gray-900 transition-colors">FAQ</a>
        </div>
      </nav>

      {/* Hero */}
      <section className="bg-gradient-to-br from-blue-950 via-blue-900 to-blue-800 text-white px-8 py-28 text-center">
        <div className="max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-blue-800/60 border border-blue-700 px-4 py-2 rounded-full text-blue-200 text-sm mb-8">
            <span className="w-2 h-2 bg-emerald-400 rounded-full" />
            Based on 2.3M+ federal procurement contracts · USASpending.gov
          </div>
          <h1 className="text-5xl font-extrabold leading-tight tracking-tight mb-6">
            You&apos;re probably overpaying<br className="hidden sm:block" /> for industrial supplies.
          </h1>
          <p className="text-blue-200 text-xl leading-relaxed mb-12 max-w-2xl mx-auto">
            Search any product to see what others actually paid. We connect you to better suppliers
            and charge 1% of your savings — nothing upfront.
          </p>
          <div className="max-w-2xl mx-auto">
            <SearchBar autoFocus />
          </div>
          <p className="mt-5 text-blue-400 text-sm">
            Try:{' '}
            {EXAMPLES.map((e, i) => (
              <span key={e}>
                <a
                  href={`/search?q=${encodeURIComponent(e)}`}
                  className="underline underline-offset-2 hover:text-blue-200 transition-colors"
                >
                  {e}
                </a>
                {i < EXAMPLES.length - 1 && ' · '}
              </span>
            ))}
          </p>
        </div>
      </section>

      {/* Stats bar */}
      <div className="bg-blue-900 text-white py-8">
        <div className="max-w-4xl mx-auto grid grid-cols-3 gap-8 text-center px-8">
          {STATS.map((s) => (
            <div key={s.label}>
              <div className="text-3xl font-black text-emerald-400">{s.value}</div>
              <div className="text-blue-300 text-sm mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* How it works */}
      <section id="how" className="max-w-5xl mx-auto px-8 py-24">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-16">How ProcureEdge works</h2>
        <div className="grid grid-cols-3 gap-12">
          {STEPS.map((s) => (
            <div key={s.n}>
              <div className="text-6xl font-black text-gray-100 mb-4 leading-none">{s.n}</div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">{s.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="bg-gray-50 border-t border-gray-100 px-8 py-20">
        <div className="max-w-2xl mx-auto space-y-8">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-10">Common questions</h2>
          {[
            {
              q: 'Where does the price data come from?',
              a: 'All price benchmarks are derived from USASpending.gov, the official source for U.S. federal contract data. Every contract over $10K is reported publicly.',
            },
            {
              q: 'When exactly do you charge the 1% fee?',
              a: 'Only after you confirm savings with a new supplier and make your first purchase. We invoice 1% of your verified first-year savings — never upfront.',
            },
            {
              q: "What if I don't save money?",
              a: 'You pay nothing. Our incentive is 100% aligned with yours: we only make money when you do.',
            },
          ].map((item) => (
            <div key={item.q}>
              <p className="font-semibold text-gray-900 mb-2">{item.q}</p>
              <p className="text-gray-500 text-sm leading-relaxed">{item.a}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="bg-white border-t border-gray-100 px-8 py-20 text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-3">Ready to find out what you should be paying?</h2>
        <p className="text-gray-400 mb-8">Free to search. 1% fee, only if we save you money.</p>
        <div className="max-w-2xl mx-auto">
          <SearchBar />
        </div>
      </section>

      <footer className="border-t border-gray-100 py-8 text-center text-gray-400 text-sm">
        © 2026 ProcureEdge · Data sourced from USASpending.gov public records
      </footer>
    </div>
  );
}
