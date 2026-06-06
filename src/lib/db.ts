import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';
import { v4 as uuid } from 'uuid';

const DATA_DIR = path.join(process.cwd(), 'data');
const DB_PATH = path.join(DATA_DIR, 'suppliers.db');

let _db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (_db) return _db;

  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

  _db = new Database(DB_PATH);
  _db.pragma('journal_mode = WAL');
  _db.pragma('foreign_keys = ON');

  _db.exec(`
    CREATE TABLE IF NOT EXISTS supplier_listings (
      id          TEXT PRIMARY KEY,
      created_at  INTEGER NOT NULL,
      company     TEXT NOT NULL,
      contact     TEXT NOT NULL,
      email       TEXT NOT NULL,
      phone       TEXT,
      description TEXT NOT NULL,
      categories  TEXT NOT NULL,
      psc_codes   TEXT NOT NULL,
      keywords    TEXT NOT NULL,
      price_min   REAL,
      price_max   REAL,
      state       TEXT,
      paid        INTEGER NOT NULL DEFAULT 0,
      active      INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS buyer_requests (
      id           TEXT PRIMARY KEY,
      created_at   INTEGER NOT NULL,
      query        TEXT NOT NULL,
      annual_spend REAL NOT NULL,
      name         TEXT NOT NULL,
      email        TEXT NOT NULL,
      company      TEXT NOT NULL,
      matched_ids  TEXT NOT NULL DEFAULT '[]',
      fee_owed     REAL
    );
  `);

  seedIfEmpty(_db);
  return _db;
}

function seedIfEmpty(db: Database.Database) {
  const count = (db.prepare('SELECT COUNT(*) as n FROM supplier_listings').get() as { n: number }).n;
  if (count > 0) return;

  const insert = db.prepare(`
    INSERT INTO supplier_listings
      (id, created_at, company, contact, email, phone, description, categories, psc_codes, keywords, price_min, price_max, state, paid, active)
    VALUES
      (@id, @created_at, @company, @contact, @email, @phone, @description, @categories, @psc_codes, @keywords, @price_min, @price_max, @state, 1, 1)
  `);

  const SEED: Omit<SupplierListing, 'id' | 'created_at'>[] = [
    {
      company: 'Fastener World Inc.',
      contact: 'Mark Reynolds',
      email: 'mark@fastenerworld.com',
      phone: '614-555-0181',
      description: 'Full-line distributor of industrial fasteners: hex bolts, cap screws, nuts, washers, rivets, anchors. All grades and materials including grade 8 steel, stainless, and titanium. Volume pricing available.',
      categories: JSON.stringify(['Fasteners', 'Hardware']),
      psc_codes: JSON.stringify(['5305', '5306', '5310', '5315', '5320', '5325']),
      keywords: 'fasteners bolts screws nuts washers rivets anchors hardware steel stainless titanium grade hex cap',
      price_min: 5000,
      price_max: 500000,
      state: 'OH',
      paid: 1,
      active: 1,
    },
    {
      company: 'Pacific Hydraulics Supply',
      contact: 'Dana Kowalski',
      email: 'dana@pachydrosupply.com',
      phone: '213-555-0242',
      description: 'Hydraulic and pneumatic components: fittings, hoses, cylinders, pumps, valves, and actuators. Parker, Eaton, and Sun Hydraulics distributor. Same-day shipping on in-stock items.',
      categories: JSON.stringify(['Hydraulics', 'Pneumatics', 'Valves']),
      psc_codes: JSON.stringify(['4820', '4810', '4730', '4935', '4320']),
      keywords: 'hydraulic pneumatic fittings hoses cylinders pumps valves actuators parker eaton sun',
      price_min: 10000,
      price_max: 2000000,
      state: 'CA',
      paid: 1,
      active: 1,
    },
    {
      company: 'Safety First Industrial Supply',
      contact: 'Priya Nair',
      email: 'priya@safetyfirstind.com',
      phone: '214-555-0367',
      description: 'Complete PPE and safety equipment supplier. Gloves, hard hats, safety vests, goggles, respirators, fall protection harnesses. OSHA-compliant products for manufacturing and construction.',
      categories: JSON.stringify(['Safety', 'PPE']),
      psc_codes: JSON.stringify(['8415', '8470', '4240', '8430', '8465']),
      keywords: 'safety ppe gloves hardhat helmet goggles respirator harness vest protective osha manufacturing',
      price_min: 2000,
      price_max: 300000,
      state: 'TX',
      paid: 1,
      active: 1,
    },
    {
      company: 'Great Lakes Precision Tools',
      contact: 'James Okafor',
      email: 'james@gllrectools.com',
      phone: '313-555-0445',
      description: 'Cutting tools and precision tooling: drill bits, end mills, taps, reamers, inserts, and saw blades. Carbide and HSS. Brands: Sandvik, Kennametal, Iscar. Tool resharpening services available.',
      categories: JSON.stringify(['Cutting Tools', 'Precision Tooling']),
      psc_codes: JSON.stringify(['5110', '5130', '5120', '5140', '3460']),
      keywords: 'cutting drill bit endmill tap reamer blade saw insert carbide hss sandvik kennametal iscar precision',
      price_min: 3000,
      price_max: 400000,
      state: 'MI',
      paid: 1,
      active: 1,
    },
    {
      company: 'Valve & Flow Solutions',
      contact: 'Sandra Chu',
      email: 'sandra@valveflowsolutions.com',
      phone: '312-555-0523',
      description: 'Industrial valve specialists: gate, ball, butterfly, check, and solenoid valves. Actuators and control systems. API and ASME certified products for oil & gas, chemical, and water treatment.',
      categories: JSON.stringify(['Valves', 'Fluid Control']),
      psc_codes: JSON.stringify(['4820', '4810']),
      keywords: 'valve valves gate ball butterfly check solenoid actuator control flow api asme oil gas chemical water',
      price_min: 8000,
      price_max: 1500000,
      state: 'IL',
      paid: 1,
      active: 1,
    },
    {
      company: 'American Abrasives Co.',
      contact: 'Tom Bradley',
      email: 'tom@americanabrasives.com',
      phone: '404-555-0619',
      description: 'Abrasive products manufacturer and distributor. Grinding wheels, flap discs, cut-off wheels, sandpaper belts, fiber discs. Norton, 3M, and Camel brands. Custom sizes available.',
      categories: JSON.stringify(['Abrasives']),
      psc_codes: JSON.stringify(['5350']),
      keywords: 'abrasive grinding wheel flap disc sandpaper belt fiber cut-off norton 3m camel polishing',
      price_min: 1000,
      price_max: 150000,
      state: 'GA',
      paid: 1,
      active: 1,
    },
    {
      company: 'Midwest MRO Direct',
      contact: 'Rachel Kim',
      email: 'rachel@midwestmrodirect.com',
      phone: '412-555-0734',
      description: 'One-stop MRO (Maintenance, Repair, Operations) supplier. Hardware, fasteners, cutting tools, safety supplies, electrical components, and more. 250,000+ SKUs in stock. Net-30 terms available.',
      categories: JSON.stringify(['MRO', 'Hardware', 'Fasteners', 'Safety', 'Electrical']),
      psc_codes: JSON.stringify(['5340', '5305', '5310', '5325', '8415', '5940']),
      keywords: 'mro maintenance repair operations hardware fasteners cutting safety electrical industrial general',
      price_min: 5000,
      price_max: 5000000,
      state: 'PA',
      paid: 1,
      active: 1,
    },
    {
      company: 'Eagle Safety Products',
      contact: 'Mike Torres',
      email: 'mike@eaglesafetyproducts.com',
      phone: '813-555-0812',
      description: 'Safety equipment for industrial, construction, and oil & gas. Respiratory protection, fall protection, eye and face protection, hearing protection, and flame-resistant clothing.',
      categories: JSON.stringify(['Safety', 'PPE', 'Respiratory']),
      psc_codes: JSON.stringify(['8415', '4240', '8470', '8465']),
      keywords: 'safety ppe respiratory fall protection eye face hearing flame resistant clothing industrial construction oil gas',
      price_min: 3000,
      price_max: 600000,
      state: 'FL',
      paid: 1,
      active: 1,
    },
    {
      company: 'Precision Bearing & Seal',
      contact: 'Yuna Chen',
      email: 'yuna@precisonbearingseal.com',
      phone: '952-555-0901',
      description: 'Bearings, seals, and related power transmission components. Ball, roller, and tapered bearings. O-rings, gaskets, lip seals, mechanical seals. SKF, NSK, Timken authorized distributor.',
      categories: JSON.stringify(['Bearings', 'Seals', 'Power Transmission']),
      psc_codes: JSON.stringify(['3110', '5330']),
      keywords: 'bearing bearings seal seals oring gasket packing ring roller ball tapered skf nsk timken',
      price_min: 4000,
      price_max: 800000,
      state: 'MN',
      paid: 1,
      active: 1,
    },
    {
      company: 'Bolt Masters of Indiana',
      contact: 'Gary Strom',
      email: 'gary@boltmasters.com',
      phone: '317-555-0998',
      description: 'Structural and high-strength fasteners for construction and heavy industry. A325/A490 structural bolts, anchor bolts, stud anchors, and headed anchor rods. AISC certified fabrication.',
      categories: JSON.stringify(['Fasteners', 'Structural']),
      psc_codes: JSON.stringify(['5305', '5306', '5325']),
      keywords: 'bolt bolts fastener structural high-strength anchor stud a325 a490 construction heavy aisc certified',
      price_min: 10000,
      price_max: 1000000,
      state: 'IN',
      paid: 1,
      active: 1,
    },
  ];

  const insertMany = db.transaction((rows: typeof SEED) => {
    for (const row of rows) {
      insert.run({ ...row, id: uuid(), created_at: Date.now() });
    }
  });
  insertMany(SEED);
}

export interface SupplierListing {
  id: string;
  created_at: number;
  company: string;
  contact: string;
  email: string;
  phone: string | null;
  description: string;
  categories: string;
  psc_codes: string;
  keywords: string;
  price_min: number | null;
  price_max: number | null;
  state: string | null;
  paid: number;
  active: number;
}

export interface BuyerRequest {
  id: string;
  created_at: number;
  query: string;
  annual_spend: number;
  name: string;
  email: string;
  company: string;
  matched_ids: string;
  fee_owed: number | null;
}
