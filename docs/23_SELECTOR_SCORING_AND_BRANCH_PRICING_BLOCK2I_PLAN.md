# Block 2I - Selector Scoring, Recommendation Ranking, and Branch Pricing

## Goal
Add quote-ready selector scoring on top of the 2H catalog-backed selector system so the quote team can see why one item is preferred, whether a branch price overlay is in play, and what item should be recommended when multiple compatible options exist.

## What this block adds
- Selector candidate scoring and ranking by family
- Branch-aware price overlays for selector items
- Recommended item flag and score breakdown
- Selector recommendation API route
- Quote Workflow UI ranking table and branch preference selector
- Selector preview/save now respect preferred branch pricing
- Saved selector templates preserve scoring and branch metadata
- Attached package workspace keeps selector scoring metadata visible

## Scope
Families supported in this slice:
- pump
- filter
- salt_system
- automation

## Acceptance
- Family selector ranking returns candidates ordered by compatibility, score, and price
- Preferred branch overlay changes effective price and price source when configured
- Selector preview uses branch-adjusted pricing
- Saved selector templates preserve preferred branch and selector scoring
- Quote Workflow displays a selector ranking table before save
- Full suite should remain green from the last verified baseline once applied locally
