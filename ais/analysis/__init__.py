"""
AIS analysis pipeline for vessel correlation and anomaly detection.

This module provides backend analytical functions for:
- Candidate filtering (temporal, spatial, trajectory)
- Association scoring (temporal, proximity, trajectory compatibility)
- Behavioral/anomaly analysis (speed, course, AIS gaps, consistency)

All analysis functions are deterministic and accept investigation context
(source region, release window) as inputs rather than hardcoding constants.
"""
