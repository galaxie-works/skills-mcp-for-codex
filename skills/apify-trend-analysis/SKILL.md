---
name: "apify-trend-analysis"
description: "Use Apify actors/datasets to collect market or social signals and produce a trend report with direction, momentum, confidence, and watchlist. Use when tracking trends across sites, keywords, products, or topics."
---

# Apify Trend Analysis

Use this skill when the goal is trend detection, not only raw scraping.

## Trigger scope

- monitor market/social trends
- compare topic momentum over time
- detect emerging signals by keyword/domain/category
- produce periodic trend briefs from scraped datasets

## Workflow

1. Define trend objective:
   - topic/keyword set
   - geography/language
   - time window
2. Collect data with Apify actors (or existing Apify datasets).
3. Normalize fields:
   - timestamp
   - source
   - metric (mentions/views/engagement/etc.)
4. Aggregate by time bucket (daily/weekly) and source.
5. Score each topic:
   - direction (up/flat/down)
   - momentum (weak/medium/strong)
   - confidence (low/medium/high)
6. Output:
   - top risers
   - top decliners
   - stable leaders
   - watchlist candidates

## Output format

- one-page summary
- table with topic, change %, momentum, confidence
- short interpretation and recommended actions

## Guardrails

- avoid single-source conclusions
- check sample size before labeling a trend
- separate short spikes from sustained growth
- keep assumptions explicit in the report

## Note

This local skill is a compatibility fallback for the `apify-trend-analysis` slug referenced on skills directories, because the exact upstream path was not publicly available at installation time.

