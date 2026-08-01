# Connector realization

## Aim

Compare fetched evidence records and distinguish active, empty, and unavailable connectors.

## Data source

Evidence rows in `ingest_health` from `data/snapshots/2026-07-31.json`.

## Chart type

Horizontal bars show both count differences and connector status.

## Script

See `scripts/generate_landscape_report_figures.py` (`figure_connectors`).
