/**
 * PSC (Product/Service Code) keyword → code mappings for industrial supplies.
 * PSC codes are the federal government's categorization system for products.
 * Used for smarter query → supplier matching.
 */

export const PSC_KEYWORD_MAP: Record<string, string[]> = {
  // Fasteners
  fastener: ['5305', '5306', '5307', '5310', '5315', '5320', '5325'],
  fasteners: ['5305', '5306', '5307', '5310', '5315', '5320', '5325'],
  bolt: ['5305', '5306'],
  bolts: ['5305', '5306'],
  screw: ['5305'],
  screws: ['5305'],
  nut: ['5310'],
  nuts: ['5310'],
  washer: ['5310'],
  washers: ['5310'],
  rivet: ['5320'],
  rivets: ['5320'],
  anchor: ['5325'],
  stud: ['5305', '5306'],
  threaded: ['5305', '5306'],

  // Hydraulics & pneumatics
  hydraulic: ['4820', '4810', '4730', '4935'],
  hydraulics: ['4820', '4810', '4730', '4935'],
  pneumatic: ['4820', '4810', '4730'],
  fitting: ['4730', '4820', '4810'],
  fittings: ['4730', '4820', '4810'],
  hose: ['4730'],
  hoses: ['4730'],
  pump: ['4320', '4935'],
  pumps: ['4320', '4935'],
  cylinder: ['4935'],
  cylinders: ['4935'],
  actuator: ['4935'],

  // Valves
  valve: ['4820', '4810'],
  valves: ['4820', '4810'],
  gate: ['4820'],
  ball: ['4820'],
  check: ['4820'],
  solenoid: ['4820', '5945'],
  regulator: ['4820', '6630'],

  // Safety / PPE
  safety: ['8415', '8470', '4240', '8430'],
  glove: ['8415'],
  gloves: ['8415'],
  hardhat: ['8415'],
  helmet: ['8415'],
  goggles: ['4240', '8415'],
  respirator: ['4240'],
  ppe: ['8415', '8470', '4240'],
  protective: ['8415', '8470', '4240'],
  harness: ['8465'],
  vest: ['8415', '8465'],

  // Cutting tools
  cutting: ['5110', '5130', '5120', '5140', '3460'],
  drill: ['5110', '5130'],
  bit: ['5110', '5130'],
  bits: ['5110', '5130'],
  mill: ['5130'],
  mills: ['5130'],
  tap: ['5140'],
  taps: ['5140'],
  reamer: ['5140'],
  blade: ['5110', '5130', '5350'],
  saw: ['5110', '5130'],
  endmill: ['5130'],
  lathe: ['3460'],
  insert: ['3460'],

  // Abrasives
  abrasive: ['5350'],
  abrasives: ['5350'],
  grinding: ['5350'],
  sandpaper: ['5350'],
  disc: ['5350'],
  wheel: ['5350'],
  belt: ['5350'],
  polishing: ['5350'],

  // Hardware
  hardware: ['5340', '5325'],
  hinge: ['5340'],
  latch: ['5340'],
  spring: ['5360'],
  springs: ['5360'],
  chain: ['4010'],
  chains: ['4010'],
  hook: ['5340'],
  bracket: ['5340'],

  // Electrical
  electrical: ['5940', '5945', '5950', '5960', '5970', '5975'],
  wire: ['6145'],
  wiring: ['6145'],
  cable: ['6145'],
  connector: ['5935'],
  connectors: ['5935'],
  relay: ['5945'],
  switch: ['5930'],
  breaker: ['5925'],
  conduit: ['5975'],
  fuse: ['5920'],

  // Bearings
  bearing: ['3110'],
  bearings: ['3110'],
  race: ['3110'],

  // Seals / Gaskets
  seal: ['5330'],
  seals: ['5330'],
  gasket: ['5330'],
  gaskets: ['5330'],
  oring: ['5330'],
  packing: ['5330'],

  // General MRO
  mro: ['5340', '5325', '5305'],
  maintenance: ['5340', '5305'],
  industrial: ['5340', '5305', '5325'],
};

export function queryToPSCCodes(query: string): string[] {
  const tokens = query
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter(Boolean);

  const codes = new Set<string>();
  for (const token of tokens) {
    const mapped = PSC_KEYWORD_MAP[token];
    if (mapped) mapped.forEach((c) => codes.add(c));
  }
  return [...codes];
}

export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((t) => t.length > 2);
}
