# PHASE 6 — AIS BEHAVIORAL/ANOMALY EVIDENCE ANALYSIS

**Status**: COMPLETE ✓

**Build**: TypeScript compilation successful (0 errors), Vite production build successful

## Overview

Phase 6 adds deterministic, explainable AIS behavioral/anomaly evidence to identify potentially unusual AIS movement characteristics. This phase does NOT replace Phase 5 Association Score — it operates as a supporting evidence layer alongside Phase 5's spatio-temporal compatibility analysis.

## Architecture

```
AIS DATA → Phase 4B Filtering → Phase 5 Association → Phase 6 Anomaly Evidence → Combined Evidence
```

## Module: aisAnomalyAnalysis.ts

**Exports**:
- `ANOMALY_CONFIG` — Centralized thresholds/weights
- `calculateSpeedDeviation()` — Speed change evidence (0–100)
- `calculateCourseChange()` — Course change evidence (0–100)
- `calculateAISGaps()` — Data gap evidence (0–100)
- `calculateTrajectoryConsistency()` — Trajectory plausibility (0–100)
- `analyzeVesselBehavior()` — Combined analysis per vessel
- `buildAnomalyAnalysis()` — Pipeline for all vessels
- Types: `AISAnomalyResult`, `AnomalyAnalysisResult`

## Thresholds (Demonstration Values)

**Speed Deviation**: 3.0 knots (demo has 15-min sampling, ±0.5 knots noise)
**Course Change**: 15.0 degrees (with circular angle handling: 359°→1° = 2°)
**AIS Data Gaps**: 30 minutes (normal interval is 15 minutes)
**Max Plausible Speed**: 25 knots (typical merchant vessel emergency speed)

**Weights** (sum = 1.0):
- Speed: 0.25
- Course: 0.25
- AIS Gap: 0.25
- Trajectory: 0.25

**Formula**: `Score = (0.25×Speed) + (0.25×Course) + (0.25×Gap) + (0.25×Trajectory)`

## Evidence Indicators

Observational, non-causation language:
- "No significant speed deviation detected" / "Significant speed change observed"
- "No significant course change detected" / "Significant course change observed"
- "No significant AIS data gap detected" / "Significant AIS data gap detected"
- "Trajectory appears continuous" / "Significant trajectory discontinuity detected"
