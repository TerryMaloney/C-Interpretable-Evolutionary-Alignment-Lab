import Link from 'next/link';
import SupplierListingForm from '@/components/SupplierListingForm';

export default function NewSupplierPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-8 py-4 flex items-center gap-6">
        <Link href="/" className="font-bold text-xl text-blue-900 tracking-tight">
          ProcureEdge
        </Link>
        <span className="text-gray-300">/</span>
        <span className="text-gray-500 text-sm">List your business</span>
      </nav>

      <div className="max-w-3xl mx-auto px-8 py-12">
        <div className="mb-10">
          <h1 className="text-3xl font-bold text-gray-900 mb-3">List your business as a supplier</h1>
          <p className="text-gray-500 leading-relaxed">
            Get matched with buyers actively looking for what you supply. We send you warm introductions — you close the deal. $1 to list for 12 months.
          </p>
        </div>

        {/* Value props */}
        <div className="grid grid-cols-3 gap-4 mb-10">
          {[
            { icon: '🎯', title: 'Qualified matches', body: 'We only intro you to buyers whose spend fits your deal size.' },
            { icon: '$', title: '$1 listing fee', body: 'Flat $1 to be visible for a year. No commissions, no hidden fees.' },
            { icon: '✓', title: 'Real buyer intent', body: 'Buyers come to us because they know they\'re overpaying. High motivation.' },
          ].map((v) => (
            <div key={v.title} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="text-2xl mb-2">{v.icon}</div>
              <p className="font-semibold text-gray-900 text-sm mb-1">{v.title}</p>
              <p className="text-gray-400 text-xs leading-relaxed">{v.body}</p>
            </div>
          ))}
        </div>

        <SupplierListingForm />
      </div>
    </div>
  );
}
