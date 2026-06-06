import { NextRequest, NextResponse } from 'next/server';
import { v4 as uuid } from 'uuid';
import { getDb, SupplierListing } from '@/lib/db';

export async function GET() {
  try {
    const db = getDb();
    const rows = db
      .prepare('SELECT * FROM supplier_listings WHERE active = 1 AND paid = 1 ORDER BY created_at DESC')
      .all() as SupplierListing[];

    const suppliers = rows.map((r) => ({
      ...r,
      categories: JSON.parse(r.categories),
      psc_codes: JSON.parse(r.psc_codes),
      email: r.email.replace(/(.{2}).*(@.*)/, '$1***$2'), // redact for public listing
    }));

    return NextResponse.json({ suppliers, total: suppliers.length });
  } catch (err: unknown) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { company, contact, email, phone, description, categories, psc_codes, price_min, price_max, state } = body;

    if (!company || !contact || !email || !description) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return NextResponse.json({ error: 'Invalid email' }, { status: 400 });
    }

    const keywords = [
      description,
      Array.isArray(categories) ? categories.join(' ') : '',
    ]
      .join(' ')
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter((t) => t.length > 2)
      .join(' ');

    const db = getDb();
    const id = uuid();

    db.prepare(`
      INSERT INTO supplier_listings
        (id, created_at, company, contact, email, phone, description, categories, psc_codes, keywords, price_min, price_max, state, paid, active)
      VALUES
        (@id, @created_at, @company, @contact, @email, @phone, @description, @categories, @psc_codes, @keywords, @price_min, @price_max, @state, @paid, 1)
    `).run({
      id,
      created_at: Date.now(),
      company,
      contact,
      email,
      phone: phone || null,
      description,
      categories: JSON.stringify(Array.isArray(categories) ? categories : []),
      psc_codes: JSON.stringify(Array.isArray(psc_codes) ? psc_codes : []),
      keywords,
      price_min: price_min ? Number(price_min) : null,
      price_max: price_max ? Number(price_max) : null,
      state: state || null,
      paid: 1, // $1 fee — mock-confirmed for beta; wire Stripe here
    });

    return NextResponse.json({ id, success: true });
  } catch (err: unknown) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
