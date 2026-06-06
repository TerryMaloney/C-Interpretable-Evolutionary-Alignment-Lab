export interface ContractRecord {
  id: string;
  recipientName: string;
  awardAmount: number;
  description: string;
  startDate: string;
  endDate: string;
  agencyName: string;
  periodDays: number;
  annualizedAmount: number;
}

export interface PriceStats {
  min: number;
  max: number;
  median: number;
  mean: number;
  p25: number;
  p75: number;
}

export interface PriceAnalysis {
  query: string;
  totalContracts: number;
  contracts: ContractRecord[];
  stats: PriceStats;
}
