import { ContractRecord, PriceAnalysis } from './types';

const BASE = 'https://api.usaspending.gov/api/v2';

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  const idx = Math.floor((p / 100) * (sorted.length - 1));
  return sorted[idx];
}

export async function searchContracts(query: string): Promise<PriceAnalysis> {
  const body = {
    filters: {
      keywords: [query],
      award_type_codes: ['A', 'B', 'C', 'D'],
      time_period: [{ start_date: '2023-01-01', end_date: '2025-06-01' }],
    },
    fields: [
      'Award ID',
      'Recipient Name',
      'Award Amount',
      'Description',
      'Start Date',
      'End Date',
      'awarding_agency_name',
    ],
    limit: 100,
    page: 1,
    sort: 'Award Amount',
    order: 'desc',
  };

  const res = await fetch(`${BASE}/search/spending_by_award/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    next: { revalidate: 3600 },
  });

  if (!res.ok) throw new Error(`USASpending API error: ${res.status}`);

  const data = await res.json();
  const raw: Record<string, unknown>[] = data.results ?? [];

  const contracts: ContractRecord[] = raw
    .filter((r) => Number(r['Award Amount']) > 0)
    .map((r) => {
      const start = String(r['Start Date'] ?? '');
      const end = String(r['End Date'] ?? '');
      const msPerDay = 1000 * 60 * 60 * 24;
      const days =
        start && end
          ? Math.max(
              (new Date(end).getTime() - new Date(start).getTime()) / msPerDay,
              1,
            )
          : 365;
      const awardAmount = Number(r['Award Amount']);
      const annualizedAmount = (awardAmount / days) * 365;

      return {
        id: String(r['Award ID'] ?? ''),
        recipientName: String(r['Recipient Name'] ?? 'Unknown'),
        awardAmount,
        description: String(r['Description'] ?? ''),
        startDate: start,
        endDate: end,
        agencyName: String(r['awarding_agency_name'] ?? ''),
        periodDays: Math.round(days),
        annualizedAmount,
      };
    });

  const amounts = contracts.map((c) => c.annualizedAmount).sort((a, b) => a - b);
  const mean = amounts.length > 0 ? amounts.reduce((a, b) => a + b, 0) / amounts.length : 0;

  return {
    query,
    totalContracts: data.page_metadata?.total ?? contracts.length,
    contracts: contracts.slice(0, 20),
    stats: {
      min: amounts[0] ?? 0,
      max: amounts[amounts.length - 1] ?? 0,
      median: percentile(amounts, 50),
      mean,
      p25: percentile(amounts, 25),
      p75: percentile(amounts, 75),
    },
  };
}
