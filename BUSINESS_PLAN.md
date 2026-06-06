# ProcureEdge — Business Plan
*Draft for review · June 2026*

---

## The One-Liner

ProcureEdge shows industrial businesses that they're overpaying for supplies — using public government contract data as a price benchmark — then connects them to better suppliers. We earn 1% of the savings. Suppliers pay $1 to list.

---

## The Problem

Industrial buyers (manufacturers, contractors, fleet operators) routinely overpay for commodity supplies — fasteners, hydraulic fittings, safety equipment, cutting tools, valves — because they have no reliable price transparency. They don't know what competitors pay. Supplier relationships are sticky and inertia is high. The average buyer renews the same supplier contract year after year without checking the market.

On the supplier side, qualified B2B leads for industrial goods are expensive and hard to find. Traditional channels (trade shows, cold outreach, distributor networks) are costly and slow.

The gap between what a high-paying buyer spends and what a competitive buyer spends for the same category of goods is routinely 20–40%. On a $200,000/year spend, that's $40,000–$80,000 left on the table annually.

---

## The Insight

The U.S. federal government publishes every contract award over $10,000 at **USASpending.gov** — 2.3+ million records including recipient, description, dollar amount, and duration. This is public, free, and updated continuously.

Within any given product category, this data shows enormous price variance between buyers for functionally identical goods. That variance is the wedge. If we can show a buyer "here's what others paid for this same category," we create immediate, credible motivation to act.

We're not the first to use USASpending.gov as a data source — but we are, as far as we know, the first to use it specifically as a *price benchmark tool for private buyers* with a connected supplier marketplace.

---

## How It Works

### Buyer Flow
1. Buyer searches any industrial supply category (e.g. "steel fasteners", "hydraulic fittings")
2. ProcureEdge pulls live federal contract data for that category and shows:
   - Price distribution: lowest, 25th percentile, median, highest paid
   - A ranked list of recent contracts (who paid what, to whom, for what agency)
3. Buyer enters their current annual spend
4. We show where they fall in the distribution and calculate their estimated overpayment
5. We show matched suppliers from our marketplace, ranked by relevance to their query and deal size
6. Buyer submits contact info, agrees to the 1% savings fee if we save them money
7. We make the introduction

### Supplier Flow
1. Supplier fills out a listing form: company info, what they supply, product categories, deal size range
2. Pays a $1 listing fee (12 months)
3. Listing is live and searchable
4. When a buyer match occurs, supplier receives a warm introduction email with buyer context

### Matching Engine
Suppliers are scored against buyer queries using:
- **PSC code matching** — queries are mapped to federal Product/Service Codes (e.g. "fasteners" → codes 5305, 5306, 5310, etc.), and suppliers are scored by how many relevant codes they cover
- **Keyword overlap** — buyer query tokens matched against supplier description and keywords
- **Price range compatibility** — buyer's stated annual spend compared to supplier's listed deal size range
- **Score normalization** — all factors combined into a 0–100 relevance score with human-readable match reasons shown to the buyer

The matching re-runs when the buyer enters their spend amount, so a small buyer ($15K/yr) doesn't get matched to a supplier whose minimum deal is $500K.

---

## Business Model

### Revenue Stream 1: Buyer-side referral fee
- **1% of verified first-year savings** when a buyer connects with a supplier through ProcureEdge and confirms they switched
- No charge if the buyer doesn't save money
- Example: buyer saves $60,000/year → we invoice $600
- Psychologically simple: "We only make money when you do"

### Revenue Stream 2: Supplier listing fee
- **$1 per listing** for 12 months of visibility
- Designed to be friction-removing: low enough that any legitimate supplier will pay it, high enough to filter pure spam
- May be raised to $25–50 as supplier verification is introduced (business email, domain check)
- Future: tiered listings (featured placement, verified badge, analytics dashboard)

### Unit Economics (illustrative)
| Scenario | Buyer Annual Spend | Savings Found | Our Fee |
|---|---|---|---|
| Small | $40,000 | $8,000 | $80 |
| Mid | $120,000 | $30,000 | $300 |
| Large | $500,000 | $100,000 | $1,000 |
| Enterprise | $2,000,000 | $400,000 | $4,000 |

To reach $100K ARR: ~333 mid-tier buyer conversions per year, or ~28/month. This is achievable if we own a single niche vertical deeply.

---

## Market

### TAM
U.S. industrial MRO (Maintenance, Repair, Operations) spend is estimated at **$700B+ annually**. The broader industrial supply market including construction, manufacturing, and government contractors is several times larger. Even capturing a fraction of 1% of this as fee revenue is substantial.

### SAM (Serviceable)
Realistically we focus on: U.S.-based private businesses spending $20K–$2M/year on industrial commodity goods (fasteners, hydraulics, safety, cutting tools, abrasives, hardware). This is a large segment of small-to-mid manufacturers, contractors, and distributors.

### Comparable businesses
- **Thomasnet** — supplier discovery, no price transparency, no savings model
- **Xometry** (manufacturing marketplace) — ~$400M revenue, demonstrates B2B industrial marketplace viability
- **SourceDay** — procurement software, enterprise-focused, no price benchmarking
- **Ariba/SAP** — enterprise procurement, $1M+ contracts, far too heavy for our target

We are not aware of a direct competitor at the intersection of: public price data + small business buyer + savings-contingent fee.

---

## What's Built (Current State)

A functional MVP web application exists at this stage. It is **not production-ready** but is demonstrable and covers the full core loop.

### Working today
- **Homepage** with hero, value proposition, search bar, and supplier CTA
- **Search results page** — queries USASpending.gov live and returns real federal contract data for any industrial keyword
- **Price intelligence panel** — median, percentiles, distribution chart, list of real contracts with recipient names and amounts
- **Savings calculator** — buyer enters annual spend, sees where they fall in the distribution, gets estimated savings and 1% fee breakdown
- **Supplier matching** — PSC code + keyword matching engine scores and ranks suppliers from our database against the buyer's query; re-ranks when spend is entered
- **Supplier listing form** — full form flow: company info → category selection → mock $1 payment → confirmation
- **Supplier database** — SQLite with 10 seeded realistic industrial suppliers as demo data
- **API layer** — `/api/search` (USASpending proxy), `/api/suppliers` (create/list), `/api/match` (matching engine)

### Tech stack
- Next.js 16 (React, TypeScript)
- Tailwind CSS
- SQLite via better-sqlite3
- USASpending.gov public API (no key required)

### What is mocked / not real yet
- **Payment** — $1 listing fee UI exists but Stripe is not wired; listings are activated for free in beta
- **Savings verification** — no mechanism to confirm a buyer actually switched and saved; currently self-reported
- **Email introductions** — no email sending infrastructure; introductions are manual
- **Auth** — no user accounts; suppliers can't manage/edit their listings
- **Rate limiting** — none; the USASpending proxy is open to abuse
- **Production database** — SQLite doesn't persist in serverless deployments; needs migration to Turso or Postgres

---

## Known Risks & Honest Caveats

### Data quality risk (significant)
Federal contract prices are not the same as commercial market prices. A $450,000 hydraulic contract for the Navy is not comparable to a $40,000 order from a factory. Our benchmark is a *proxy*, not ground truth. We partially address this by showing the full distribution and raw contract details, but a buyer could make a bad decision based on misreading the data. Mitigation: clear disclaimers, long-term supplement with commercial price data sources.

### Legal: broker licensing
In most states and for most industrial goods, operating as an introduction broker requires no license. However, some edge cases exist (certain chemicals, defense-related goods, specific state regulations). We are not legal counsel and this needs a quick review from a business attorney before scaling. Estimated cost: $500–1,500 for an initial opinion.

### Legal: anti-kickback (federal contractor context)
If a buyer is a federal prime contractor using our service to find sub-suppliers, the combination of supplier listing fees + buyer referral fees could technically implicate the Anti-Kickback Act. Mitigation: add a clear disclaimer and consider blocking or flagging federal contractor buyers from the savings-fee model.

### Savings verification problem
"1% of savings" is a compelling pitch but hard to enforce. If a buyer says they didn't save enough to owe us anything, we can't easily verify. Options: (a) require the buyer to share first invoice from new supplier, (b) charge a flat referral fee instead of %, (c) operate on trust and treat it as brand-building if buyers don't pay. This needs a decision before scaling.

### Cold start / thin supplier database
Ten seeded suppliers cover major categories but not niche ones. A buyer searching "tungsten carbide inserts" or "pneumatic actuators" may get zero matches. We need either a targeted onboarding push in a chosen vertical, or a data pipeline to seed suppliers from public directories (Thomasnet is scrapable).

### $1 fee is too low to deter spam
Realistic problem at scale: bad actors could flood the supplier database with fake listings. Fix: require business email domains (no @gmail), domain verification via DNS TXT record, or raise the fee.

---

## What We Don't Know Yet (Key Validation Questions)

1. **Do buyers actually trust federal contract data as a price benchmark?** The core product assumes they will — but the federal/commercial price gap could undermine credibility if buyers notice it immediately.

2. **Is the savings conversion rate viable?** If 1 in 20 buyers who see savings > 0 actually follow through with an introduction request, and 1 in 5 of those actually switch suppliers, the funnel math needs to work at a traffic level we can reach.

3. **Will suppliers pay even $1?** Industrial B2B suppliers are skeptical of new directories. The $1 might be easy to say yes to, or it might still create friction if the product isn't trusted yet.

4. **Which vertical should we go deep in first?** Fasteners, hydraulics, safety, and cutting tools all seem viable. One vertical, deeply served with a curated supplier network, is more valuable than broad thin coverage.

---

## What Needs to Happen Next

### Immediate (before showing anyone with money)
- Wire Stripe for the $1 listing fee (proof of concept for monetization)
- Add disclaimer language: "Federal contract prices are benchmarks, not commercial quotes"
- Rate-limit the search API

### Short term (0–60 days)
- Pick one vertical and hand-onboard 20–30 real suppliers in it
- Build a simple email introduction flow (even just a mailto: to start)
- Migrate database to something persistent (Turso is one line of config)
- Talk to 10 real industrial buyers about the pain point

### Medium term (60–180 days)
- Savings verification flow (first invoice upload or self-attestation with follow-up)
- Supplier management dashboard (edit listing, see match volume, upgrade to featured)
- Commercial price data supplement (GSA Schedule prices are published and structured)
- Business email + domain verification for supplier listings

---

## Summary

This is a real problem (industrial buyers overpay, have no price transparency), with real public data to power it (USASpending.gov), a clean business model (1% of savings, $1 listing), and no obvious direct competitor at this intersection. The core loop is built and demonstrable.

The biggest open questions are: data credibility (federal vs commercial prices), savings enforcement, and whether we can generate enough supplier supply in a chosen vertical to make the buyer experience compelling. None of these are fatal — they're normal early-stage validation questions.

The product is at the "show a smart person and get honest feedback" stage, which is exactly where it should be.

---

*Built with Next.js + USASpending.gov public API. All price data sourced from public federal procurement records.*
