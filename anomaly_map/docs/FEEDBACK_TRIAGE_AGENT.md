# Feedback Triage Agent — Design Document

## Purpose

An LLM-based triage agent that processes public feedback submissions before human review.
The agent classifies, scores, and summarizes incoming feedback to make human review faster
and more consistent.

## What the agent does

- Classifies feedback type (dataset suggestion / bad data / explanation / source / feature request)
- Deduplicates against existing suggestions and layers
- Scores submission quality on 8 dimensions (0–5 each)
- Flags privacy, legal, and reputation risks
- Recommends next action
- Writes a 1–3 sentence review summary

## What the agent does NOT do

- Add data directly to core layers
- Treat user claims as verified
- Publish personal information
- Accept private medical records
- Expose home addresses
- Imply proof of UAP/NHI claims
- Override human reviewer decisions

All map updates require human approval after agent recommendation.

---

## Input Schema

```json
{
  "id": "uuid",
  "created_at": "ISO8601",
  "feedback_type": "dataset_suggestion | bad_data_report | explanation_suggestion | source_submission | feature_request | other",
  "title": "string",
  "description": "string",
  "source_url": "string | null",
  "related_map_url": "string | null",
  "related_hotspot_slug": "string | null",
  "submitter_email_optional": "string | null",
  "raw_payload": "object",
  "dataset_name": "string | null",
  "has_lat_lon": "yes | no | unknown | null",
  "has_timestamps": "yes | no | unknown | null",
  "public_access": "yes | no | unknown | null",
  "why_relevant": "string | null",
  "known_limitations": "string | null",
  "problem_type": "string | null",
  "correction_summary": "string | null",
  "proposed_explanation": "string | null",
  "evidence_for_explanation": "string | null",
  "confidence": "low | medium | high",
  "public_source_confirmed": "boolean"
}
```

---

## Triage Rubric (0–5 each)

| Dimension | 0 | 3 | 5 |
|---|---|---|---|
| **Public accessibility** | Requires login/payment | Partial access | Fully public, no registration |
| **Geocoded location quality** | No coordinates | City/county level | Precise lat/lon available |
| **Timestamp quality** | No dates | Year only | Full date + time |
| **Source credibility** | Anonymous blog | Community-maintained | Government/institutional/peer-reviewed |
| **Independence from existing layers** | Exact duplicate | Partial overlap | Fully independent new signal |
| **Bias/confound risk** | Very high (military/coastal/population) | Moderate | Low, well-controlled |
| **Ease of ingestion** | Manual only, no API | Semi-structured | Machine-readable API or CSV |
| **Convergence relevance** | Thematic only | Adjacent relevance | Directly strengthens C-Score computation |

**Total possible: 40 points**

---

## Recommendation Thresholds

| Score | Recommendation |
|---|---|
| 32–40 | **Fast-track** — Immediate staging for data team review |
| 22–31 | **Good backlog item** — Worth reviewing next sprint |
| 14–21 | **Context-only layer** — Useful for UX/notes, not scoring |
| 8–13  | **Needs manual review** — Insufficient info to score |
| 0–7   | **Reject / do not use** — Privacy risk, low quality, or scope violation |

---

## Privacy / Risk Flags

The agent must check for and flag:

```
PRIVACY_RISK: Contains home address, personal identifier, or medical record
LEGAL_RISK: Contains accusation against named individual without public-record basis
REPUTATION_RISK: Names specific person/organization without verifiable public claim
SCOPE_VIOLATION: Requests monetization, user accounts, or AI chatbot features (frozen scope)
DISINFORMATION_RISK: Source is known misinformation outlet or fabricated data
DUPLICATE: Substantively identical to existing layer or prior submission
```

If any flag is set, the recommendation is auto-downgraded to "Needs manual review" minimum.
PRIVACY_RISK auto-sets to "Reject."

---

## Output Schema

```json
{
  "id": "uuid",
  "triage_status": "Fast-track | Good backlog item | Context-only layer | Needs manual review | Reject",
  "triage_score": 0,
  "dimension_scores": {
    "public_accessibility": 0,
    "geocoded_location_quality": 0,
    "timestamp_quality": 0,
    "source_credibility": 0,
    "independence": 0,
    "bias_confound_risk": 0,
    "ease_of_ingestion": 0,
    "convergence_relevance": 0
  },
  "flags": [],
  "triage_summary": "1–3 sentence summary of what was submitted and why the recommendation was made",
  "reviewer_notes": "What the human reviewer should check before final decision",
  "final_decision": null,
  "reviewed_by": null,
  "reviewed_at": null
}
```

---

## Prompt Template (Claude API call)

```python
SYSTEM = """
You are a dataset quality triage agent for a geospatial anomaly correlation research project.
Your job is to evaluate public feedback submissions and score them on 8 dimensions.

Rules:
- You do not add data to the map. You only score and recommend.
- You do not treat user claims as verified facts.
- You flag privacy and legal risks conservatively.
- You do not call anything "proof," "confirmed," "alien," or "non-human intelligence."
- You evaluate source quality, not claim quality.
- A high-quality source about a mundane phenomenon is better than a low-quality source about an extraordinary claim.

Output JSON only. No preamble.
"""

USER_TEMPLATE = """
Evaluate this feedback submission:

Type: {feedback_type}
Title: {title}
Description: {description}
Source URL: {source_url}
Has lat/lon: {has_lat_lon}
Has timestamps: {has_timestamps}
Public access: {public_access}
Why relevant: {why_relevant}
Known limitations: {known_limitations}
Submitter confidence: {confidence}
Public source confirmed: {public_source_confirmed}

Existing layers (for deduplication check):
{existing_layer_names}

Score each dimension 0–5. Output JSON matching the triage output schema exactly.
"""
```

---

## Integration Notes

### Trigger
- Run after each feedback form submission
- Also available as batch job for backlog processing

### Storage
- Write triage output to `feedback` table `triage_*` columns
- Status transitions: New → Triaged → (human reviews) → Final decision

### Human review queue
- Sort by triage_score descending
- Show dimension scores + flags + summary
- Reviewer can accept, modify, or reject recommendation
- Only after final_decision = "Approved for research" does data enter staging pipeline

### Rate limiting
- Max 1 LLM call per submission
- Cache identical submissions (same title + source_url hash)
- Daily batch mode for low-priority items

---

## Example Output

```json
{
  "id": "fb-001",
  "triage_status": "Good backlog item",
  "triage_score": 27,
  "dimension_scores": {
    "public_accessibility": 4,
    "geocoded_location_quality": 3,
    "timestamp_quality": 3,
    "source_credibility": 4,
    "independence": 4,
    "bias_confound_risk": 3,
    "ease_of_ingestion": 3,
    "convergence_relevance": 3
  },
  "flags": [],
  "triage_summary": "Suggestion for Chilean CEFAA official case database. Government-run agency with scientific investigation committee. CSV downloadable from public website with coordinates and dates. Partially overlaps existing FOIA/maritime layers but covers independent South American geography not currently represented.",
  "reviewer_notes": "Verify CSV endpoint is still active. Confirm English field names or assess translation requirement. Check for duplicate coverage with existing foia_documents layer.",
  "final_decision": null
}
```

---

*Design doc — implementation pending feedback storage backend.*
*Agent does not modify core data. Human approval required for all map changes.*
