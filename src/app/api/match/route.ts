import { NextRequest, NextResponse } from 'next/server';
import { getDb, SupplierListing } from '@/lib/db';
import { matchSuppliers } from '@/lib/matching';

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get('q')?.trim();
  const spendParam = req.nextUrl.searchParams.get('spend');

  if (!q) return NextResponse.json({ error: 'Missing query' }, { status: 400 });

  try {
    const db = getDb();
    const suppliers = db
      .prepare('SELECT * FROM supplier_listings WHERE active = 1 AND paid = 1')
      .all() as SupplierListing[];

    const spend = spendParam ? parseFloat(spendParam) : undefined;
    const matches = matchSuppliers(q, suppliers, spend, 5);

    return NextResponse.json({ matches, query: q, total: suppliers.length });
  } catch (err: unknown) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
