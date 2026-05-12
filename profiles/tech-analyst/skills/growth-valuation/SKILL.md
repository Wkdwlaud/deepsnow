---
name: growth-valuation
description: "Growth stock valuation methods: PEG for profitable companies, Future Market Cap Method for early-stage. Includes RED LINES that must never be violated."
version: 1.0.0
---

# Growth Stock Valuation Toolkit

## RED LINES (硬编码，不可违反)

1. **NEVER** use "PE is too high" as a reason to reject a growth stock
2. **NEVER** apply value-stock metrics (low PE/PB/high dividend) to growth stocks
3. **ALWAYS** use the appropriate tool for the company's stage:
   - Has stable profits → PEG
   - No profits / early stage → Future Market Cap Method
   - High growth but volatile margins → PS as auxiliary

吴伟志原话: "如果一个成长股投资者跟我讲PE贵所以贵了，我就不跟他讨论。就相当于你用一个尺子来称一个东西的重量一样。"

---

## Tool 1: PEG (for profitable growth stocks)

**When to use**: Company has stable, positive earnings and visible 3-year growth.

```
PEG = Current PE / Expected 3-year CAGR of earnings (%)

Example:
- PE = 40x, Expected growth = 100% → PEG = 0.4 (CHEAP)
- PE = 20x, Expected growth = 10% → PEG = 2.0 (EXPENSIVE)
```

| PEG Range | Interpretation |
|-----------|---------------|
| < 0.5 | Significantly undervalued — strong buy zone |
| 0.5 - 0.8 | Attractive — good entry point |
| 0.8 - 1.0 | Fair value |
| 1.0 - 1.5 | Slightly expensive, hold if thesis intact |
| > 1.5 | Expensive — unless growth is accelerating |

**Key**: The growth rate denominator must be FORWARD-LOOKING (next 3 years), not trailing.

---

## Tool 2: Future Market Cap Method (for early-stage / unprofitable companies)

**When to use**: Company has no profits or is too early for PE-based valuation.

```
Future Market Cap = Industry TAM × Company's Achievable Share × Net Margin × Fair PE

Then compare: Future Market Cap / Current Market Cap = Upside Multiple

Example (AI SaaS company):
- Industry TAM in 5 years: ¥500B
- Company achievable share: 10% → ¥50B revenue
- Expected net margin at scale: 20% → ¥10B profit
- Fair PE for mature SaaS: 25x → ¥250B market cap
- Current market cap: ¥30B
- Upside: 250/30 = 8.3x → ATTRACTIVE (>5x threshold)
```

| Upside Multiple | Interpretation |
|-----------------|---------------|
| > 10x | Exceptional opportunity (if thesis is sound) |
| 5-10x | Attractive — worth heavy research |
| 3-5x | Moderate — satellite position candidate |
| < 3x | Limited upside — only if very high certainty |

**吴伟志**: "未来有1万亿市值，你有十倍的空间，那就不贵。"

---

## Tool 3: PS (Price-to-Sales) — Auxiliary Only

**When to use**: High-growth company with volatile or negative margins. NEVER as sole basis.

```
PS = Market Cap / Annual Revenue

Compare to:
- Industry peers' PS range
- Company's own historical PS range
- Implied future profit margin needed to justify current PS
```

PS is a sanity check, not a decision tool. Always pair with Future Market Cap Method.

---

## Applying to Stock Pool Decisions

| Valuation Result | Pool Action |
|-----------------|-------------|
| PEG < 0.8 or Future MCap >5x | Promote to Watch/Satellite (begin Phase 1 research) |
| PEG 0.8-1.2 or Future MCap 3-5x | Hold in current tier |
| PEG > 1.5 or Future MCap <3x | Flag for review (possible downgrade) |

---

## Common Mistakes to Avoid

1. Using trailing PE without growth context → use PEG instead
2. Comparing a 100% grower's PE to a 10% grower's PE → meaningless comparison
3. Applying PE to a pre-profit company → use Future Market Cap Method
4. Ignoring margin expansion potential in PS analysis
5. Using industry average PE without adjusting for growth differential
