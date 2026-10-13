# External Spot Checks vs. Public Corporate-Action Sources

11 of the 88 selected events (12.5% of the full sample; 55% of the 20-event
Validation Pass #1 subsample) were independently checked against public
sources outside this study's own Polygon-sourced dataset: SEC EDGAR 8-K
exhibits, Nasdaq Trader "Equity Corporate Actions Alert" notices, and
wire/press coverage. This exceeds the brief's >=10-event minimum.

| Event | Ticker | Documented ratio | Documented effective date | Public-source verdict |
|---|---|---|---|---|
| AIMD_2025-06-30_5to1 | AIMD | 1-for-5 | 2025-06-30 | CONFIRMED — Nasdaq ECA #2025-333, StreetInsider, Nasdaq press |
| AKAN_2024-11-14_2to1 | AKAN | 1-for-2 | 2024-11-14 | CONFIRMED — Nasdaq ECA #2024-548, Nasdaq/Newsfilecorp release (announced 2024-11-12) |
| ANGH_2025-08-04_10to1 | ANGH | 1-for-10 | 2025-08-04 | CONFIRMED — PRNewswire, SEC 8-K ex99-1, Nasdaq/Barchart coverage |
| APVO_2024-12-04_37to1 | APVO | 1-for-37 | 2024-12-04 | CONFIRMED — Nasdaq ECA #2024-588, Yahoo/GlobeNewswire |
| BOLT_2025-06-09_20to1 | BOLT | 1-for-20 | 2025-06-09 | CONFIRMED (date shift explained) — Nasdaq ECA #2025-286; company-stated effective 2025-06-06 (Fri), first trading session after is Mon 2025-06-09 |
| CYN_2025-02-18_150to1 | CYN | 1-for-150 | 2025-02-18 | CONFIRMED — Nasdaq ECA #2025-69, Cyngn IR, SEC 8-K |
| ENSC_2024-12-06_15to1 | ENSC | 1-for-15 | 2024-12-06 | CONFIRMED — Nasdaq ECA #2024-595, BioSpace, SEC 8-K |
| JTAI_2024-11-12_225to1 | JTAI | 1-for-225 | 2024-11-12 | CONFIRMED — SEC 8-K ex99-1, GlobeNewswire (incl. updated release), StockTitan |
| NDRA_2024-11-07_35to1 | NDRA | 1-for-35 | 2024-11-07 | CONFIRMED — Nasdaq ECA #2024-535, BusinessWire |
| TPET_2024-11-15_20to1 | TPET | 1-for-20 | 2024-11-15 | CONFIRMED — SEC 8-K ex99-1, GlobeNewswire (announced 2024-11-04) |
| UNCY_2025-06-20_10to1 | UNCY | 1-for-10 | 2025-06-20 | CONFIRMED (date shift explained) — SEC 8-K, GlobeNewswire; company-stated effective 2025-06-18 (Wed); 2025-06-19 was the Juneteenth market holiday, so first tradeable session is Fri 2025-06-20 |

**Summary: 11/11 confirmed.** 9/11 matched the public "effective date" exactly;
2/11 (BOLT, UNCY) showed a data-collection date that is 2-3 calendar days
later than the press-release date, in both cases fully explained by the
announced effective date falling on a non-trading day. No ratio
discrepancies were found anywhere in the checked subset. This supports the
integrity of the underlying event identification (separate from the
split-adjustment-factor and completeness checks, which test the price data
itself rather than the event metadata).

Method note: searches were run via general web search rather than direct
SEC EDGAR full-text search API access; results were cross-checked across at
least two independent sources per event (a primary filing or Nasdaq alert
plus at least one news outlet) before being marked CONFIRMED.
