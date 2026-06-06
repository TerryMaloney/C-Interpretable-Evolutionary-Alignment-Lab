import { SupplierListing } from './db';
import { queryToPSCCodes, tokenize } from './psc-codes';
import { PriceStats } from './types';

export interface MatchedSupplier {
  id: string;
  company: string;
  contact: string;
  email: string;
  description: string;
  categories: string[];
  state: string | null;
  price_min: number | null;
  price_max: number | null;
  score: number;
  scoreBreakdown: {
    pscMatch: number;
    keywordMatch: number;
    priceCompatibility: number;
    descriptionMatch: number;
  };
  matchReasons: string[];
}

/**
 * Score a single supplier against a buyer query.
 *
 * Scoring rubric (max ~120 before normalization):
 *   PSC code match      25 pts per matching code (capped at 50)
 *   Keyword match       8 pts per query token in supplier keywords (capped at 40)
 *   Description match   5 pts per query token in description (capped at 20)
 *   Price compatibility 15 pts if buyer budget falls within supplier range
 *
 * Final score is normalized to 0–100.
 */
export function scoreSupplier(
  query: string,
  supplier: SupplierListing,
  buyerAnnualSpend?: number,
): MatchedSupplier | null {
  const queryTokens = tokenize(query);
  const queryPSC = queryToPSCCodes(query);
  const supplierPSC: string[] = JSON.parse(supplier.psc_codes || '[]');
  const supplierKeywords = tokenize(supplier.keywords);
  const supplierDescTokens = tokenize(supplier.description);

  let pscMatch = 0;
  const matchedPSC: string[] = [];
  for (const code of queryPSC) {
    if (supplierPSC.includes(code)) {
      pscMatch += 25;
      matchedPSC.push(code);
    }
  }
  pscMatch = Math.min(pscMatch, 50);

  let keywordMatch = 0;
  const matchedKeywords: string[] = [];
  for (const token of queryTokens) {
    if (supplierKeywords.includes(token)) {
      keywordMatch += 8;
      matchedKeywords.push(token);
    }
  }
  keywordMatch = Math.min(keywordMatch, 40);

  let descriptionMatch = 0;
  for (const token of queryTokens) {
    if (supplierDescTokens.includes(token)) descriptionMatch += 5;
  }
  descriptionMatch = Math.min(descriptionMatch, 20);

  let priceCompatibility = 0;
  if (
    buyerAnnualSpend &&
    buyerAnnualSpend > 0 &&
    supplier.price_min !== null &&
    supplier.price_max !== null
  ) {
    if (
      buyerAnnualSpend >= supplier.price_min &&
      buyerAnnualSpend <= supplier.price_max * 2
    ) {
      priceCompatibility = 15;
    } else if (buyerAnnualSpend >= supplier.price_min * 0.5) {
      priceCompatibility = 8;
    }
  }

  const rawScore = pscMatch + keywordMatch + descriptionMatch + priceCompatibility;
  if (rawScore === 0) return null;

  // Normalize to 0–100
  const MAX_POSSIBLE = 50 + 40 + 20 + 15;
  const score = Math.min(Math.round((rawScore / MAX_POSSIBLE) * 100), 100);

  // Human-readable match reasons
  const matchReasons: string[] = [];
  if (matchedPSC.length > 0) matchReasons.push(`Matches ${matchedPSC.length} product category code(s)`);
  if (matchedKeywords.length > 0)
    matchReasons.push(`Stocks: ${matchedKeywords.slice(0, 3).join(', ')}`);
  if (priceCompatibility > 0) matchReasons.push('Deal size within range');

  return {
    id: supplier.id,
    company: supplier.company,
    contact: supplier.contact,
    email: supplier.email,
    description: supplier.description,
    categories: JSON.parse(supplier.categories || '[]'),
    state: supplier.state,
    price_min: supplier.price_min,
    price_max: supplier.price_max,
    score,
    scoreBreakdown: { pscMatch, keywordMatch, priceCompatibility, descriptionMatch },
    matchReasons,
  };
}

export function matchSuppliers(
  query: string,
  suppliers: SupplierListing[],
  buyerAnnualSpend?: number,
  topN = 5,
): MatchedSupplier[] {
  const scored = suppliers
    .filter((s) => s.active === 1 && s.paid === 1)
    .map((s) => scoreSupplier(query, s, buyerAnnualSpend))
    .filter((s): s is MatchedSupplier => s !== null)
    .sort((a, b) => b.score - a.score);

  return scored.slice(0, topN);
}

/** Estimate savings relative to market benchmarks */
export function estimateSavings(
  annualSpend: number,
  stats: PriceStats,
  matchedSuppliers: MatchedSupplier[],
): {
  estimatedSavings: number;
  fee: number;
  netSavings: number;
  savingsRange: { low: number; high: number };
  confidence: 'high' | 'medium' | 'low';
} {
  const overpayment = Math.max(0, annualSpend - stats.p25);

  // Range: conservative (vs median) and optimistic (vs p25)
  const savingsLow = Math.max(0, annualSpend - stats.median) * 0.7;
  const savingsHigh = overpayment;
  const estimatedSavings = Math.max(0, annualSpend - stats.p25);
  const fee = estimatedSavings * 0.01;
  const netSavings = estimatedSavings - fee;

  const confidence =
    matchedSuppliers.length >= 3 && matchedSuppliers[0].score >= 60
      ? 'high'
      : matchedSuppliers.length >= 1 && matchedSuppliers[0].score >= 30
      ? 'medium'
      : 'low';

  return {
    estimatedSavings,
    fee,
    netSavings,
    savingsRange: { low: savingsLow, high: savingsHigh },
    confidence,
  };
}
