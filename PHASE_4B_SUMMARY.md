# Phase 4B Implementation Summary

## Overview
Phase 4B — AIS Candidate Filtering has been successfully implemented for the SIH26143 maritime oil-spill investigation dashboard. The implementation adds spatio-temporal filtering logic to convert the complete historical AIS vessel set into a smaller set of "investigation candidates" based on:

1. **Temporal overlap** with the probable oil-release window
2. **Spatial proximity** to the probable source region
3. **Trajectory intersection** with the source region

This phase is **candidate filtering only** — no association scoring, ranking, anomaly detection, or responsibility classification.

---

## Files Created

### 1. `src/analysis/aisCandidateFilter.ts` (5,651 bytes)
Dedicated filtering module containing all candidate analysis logic.

**Configuration Constants:**
- `CANDIDATE_FILTER_CONFIG`:
  - `SOURCE_PROXIMITY_THRESHOLD_KM: 15`
  - `RELEASE_WINDOW_START: '2024-12-31T22:00:00Z'`
  - `RELEASE_WINDOW_END: '2025-01-01T02:00:00Z'`
- `SOURCE_REGION_BOUNDS`: 18.42–18.48°N, 72.65–72.76°E
- `SOURCE_REGION_CENTER`: 18.45°N, 72.70°E

**Filtering Functions:**
- `haversineDistanceKm()` — Calculate geographic distance
- `isTimestampInReleaseWindow()` — Check release window membership
- `filterByReleaseWindow()` — Vessel has points during window
- `calculateMinimumSourceDistance()` — Closest approach to source
- `filterBySourceProximity()` — Within 15 km threshold
- `checkTrajectorySourceIntersection()` — Passes through source region during window
- `analyzeVessel()` — Analyze single vessel
- `buildAISCandidates()` — Analyze all vessels
- `calculateCandidateStats()` — Summary statistics

**Exported Types:**
```typescript
interface AIScandidateFilterResult {
  mmsi: number
  vesselName: string
  vesselType: string
  temporalMatch: boolean
  minimumSourceDistanceKm: number
  sourceRegionProximityMatch: boolean
  trajectorySourceIntersection: boolean
  isCandidate: boolean
}

interface CandidateFilterStats {
  totalVessels: number
  temporalMatches: number
  proximityMatches: number
  intersectionMatches: number
  investigationCandidates: number
}
```

---

## Files Modified

### 1. `src/App.tsx` (3,094 bytes)
- Added: `import { buildAISCandidates, calculateCandidateStats } from './analysis/aisCandidateFilter'`
- Added: `import { useMemo } from 'react'`
- Computed:
  - `candidateResults = buildAISCandidates(DEMO_AIS_DATASET)` (memoized)
  - `candidateStats = calculateCandidateStats(candidateResults)` (memoized)
  - `candidatesByMmsi` — Fast lookup map (memoized)
- Pass `candidateStats` and `selectedVesselCandidate` to `InvestigationPanel`

### 2. `src/components/InvestigationPanel.tsx` (112 lines)
- Added props: `candidateStats`, `selectedVesselCandidate`
- Updated all phase badges: "Phase 4A" → "Phase 4B"
- **No-selection mode**: AIS Investigation summary
  - Total AIS Vessels, Temporal Matches, Proximity Matches, Investigation Candidates
- **Vessel selected**: Vessel details + Candidate Evidence section
  - Temporal Match, Source Proximity (km), Proximity Match, Trajectory Intersection, Investigation Candidate
- **Detection displayed**: Shows candidate count in AIS Investigation section
- Language: neutral, transparent (no suspect/culprit terminology)

---

## Filtering Rules Implemented

### A. Temporal Overlap
Vessel has ≥1 AIS point during 2024-12-31T22:00:00Z → 2025-01-01T02:00:00Z

**Implementation**: `filterByReleaseWindow()` — uses `some()` array check

### B. Source Region Proximity
Minimum distance from any trajectory point to source center ≤ **15 km**

**Implementation**: `calculateMinimumSourceDistance()` — Haversine formula (Earth radius: 6,371 km)

### C. Trajectory Intersection
Trajectory has point within source bounds (18.42–18.48°N, 72.65–72.76°E) AND timestamped during release window

**Implementation**: `checkTrajectorySourceIntersection()` — bounds check + time check

### Candidate Logic
```typescript
isCandidate = temporalMatch || sourceRegionProximityMatch || trajectorySourceIntersection
```
A vessel is a candidate if it satisfies **ANY** criterion.

---

## Demo Data Results

**Input**: 8 synthetic vessels

**Expected Candidates** (4–5 vessels):
- MT OCEAN TRADER (419001234) — YES (temporal + proximity)
- BULK HORIZON (352004521) — YES (temporal + proximity + intersection)
- FISHING VESSEL 001 (268005634) — YES (temporal + proximity)
- TUG PILOT ASSIST (537006847) — YES (temporal + proximity)

**Non-Candidates** (3–4 vessels):
- CONTAINER EXPRESS, CARGO FRONTIER, CONTAINER STAR, TANKER GUARDIAN — All outside 15 km threshold

---

## Build & Verification

✓ TypeScript compilation clean  
✓ Vite build succeeds in 2.38s  
✓ No errors or warnings  
✓ All 8 vessels render  
✓ Spill/drift/source region intact  
✓ AIS layer toggle works  
✓ Vessel selection works  
✓ InvestigationPanel displays correctly  

---

## Architecture

**Separation of Concerns:**
- Analysis: `src/analysis/aisCandidateFilter.ts` (pure functions)
- UI: `src/components/InvestigationPanel.tsx`
- Orchestration: `src/App.tsx`

**Performance**: O(n) on 8 vessels, memoized, no network calls

**Type Safety**: Full TypeScript, no `any` types

**Determinism**: Haversine formula, explicit thresholds, no ML/randomness

---

## What Was NOT Implemented

Per specification, intentionally excluded:
- Association scoring
- Vessel ranking
- Anomaly detection
- Responsibility claims
- "Suspect" classification
- Backend API
- Complex filtering UI
- Visual distinction on map
- Machine learning

---

## Stop Condition Reached

✓ Phase 4B complete  
✓ Build succeeds  
✓ Phase 1–4A preserved  
✓ Filtering deterministic  
✓ UI neutral

**Do NOT proceed to Phase 5**
