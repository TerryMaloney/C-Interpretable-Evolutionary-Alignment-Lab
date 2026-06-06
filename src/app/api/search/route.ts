import { NextRequest, NextResponse } from 'next/server';
import { searchContracts } from '@/lib/uspending';

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get('q')?.trim();
  if (!q) return NextResponse.json({ error: 'Missing query' }, { status: 400 });

  try {
    const results = await searchContracts(q);
    return NextResponse.json(results);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
