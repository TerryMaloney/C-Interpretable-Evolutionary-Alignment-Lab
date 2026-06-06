'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface Props {
  defaultValue?: string;
  autoFocus?: boolean;
  dark?: boolean;
}

export default function SearchBar({ defaultValue = '', autoFocus, dark }: Props) {
  const [query, setQuery] = useState(defaultValue);
  const router = useRouter();

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) router.push(`/search?q=${encodeURIComponent(query.trim())}`);
  };

  return (
    <form onSubmit={submit} className="flex gap-3 w-full">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search any industrial supply..."
        autoFocus={autoFocus}
        className={`flex-1 px-5 py-4 rounded-xl text-gray-900 text-base focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-sm border ${dark ? 'border-blue-600 bg-white/10 placeholder:text-blue-300 text-white' : 'border-gray-200 bg-white'}`}
      />
      <button
        type="submit"
        className="px-7 py-4 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold rounded-xl shadow-sm transition-colors whitespace-nowrap"
      >
        Search →
      </button>
    </form>
  );
}
