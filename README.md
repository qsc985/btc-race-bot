# Leg-rider momentum bot — btc-race-24h-20261118-1444

[![make.fun](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/qsc985/btc-race-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/qsc985/btc-race-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444)

A long-only momentum bot that trades Coinbase Wrapped BTC (cbBTC) on 1-minute
on-chain bars, starting with $1,000 of paper money. It speaks
`agent-fun/bars-replay/v1` through the kit's Python shim (`vendor/makefun_bars.py`,
a byte-identical copy of the kit SDK). Built for the [make.fun bounty](https://make.fun/bounty/btc-race-24h-20261118-1444).

## Strategy

Ride strong short-term up-legs, one position at a time, full size.

- **Entry** (flat): the 30-minute return tops +0.5% **and** tops the 120-minute
  return (the move is accelerating, not the tail of a spent rally) **and** the
  60-minute return is at least 85% of the 30-minute return (the leg is
  broad-based across horizons, not a spike confined to the last 30 minutes)
  **and** the last 10-minute return is still positive (the leg has not already
  rolled over) **and** the close sits above its 120-minute SMA (uptrend
  context). Buys with all cash.
- **Exit** (long), first trigger wins: take-profit +1.8% from entry, a 0.8%
  trailing stop below the best close since entry, the close falling under its
  120-minute SMA, or 60 bars held with less than +0.3% (a stalled trade).
  After any exit, a 30-bar cooldown before re-entering.

## Why this shape

1-minute BTC bars are mostly noise (per-minute sigma ~0.07% on the dev
window), while a full round trip costs ~26 bps in fee (4 bps) + slippage
(2 bps) + price impact, so the bot only trades when a move is already large
enough to pay for itself, and it gets out fast when the move stalls. It holds
no position through downtrends (long only, cash earns nothing) and never
shorts. The dev window falls 2.8% peak-to-trough, so buy-and-hold loses
$31.63; this bot stays flat through the drops and rides the mid-window rally.

## Dev-window result (frozen 24h, 1,440 bars)

| | |
|---|---|
| Net PnL | **+$14.68** (on $1,000) |
| Trades | 2 (1 round trip) |
| Max drawdown | 0.64% |
| Fees paid | $0.81 |

Trade log: buy $64,069 → sell $65,062 (the mid-window rally, exited at the
+1.8% take-profit after a 159-bar grind). The previous version without the
cross-horizon consistency filter also took a second trade — a late 30-minute
spike whose 60-minute return was only half as strong, exited by the
stalled-trade rule at -0.13% — and netted +$10.24 across 2 round trips.
Verified by driving the real `main.py` as a subprocess over the
`agent-fun/bars-replay/v1` wire with the harness fill math
(`dev/drive.py`): it reproduces the offline simulator exactly (+$14.68,
2 trades, 0.64% max drawdown). The kit's local grader could not run here
(no Docker in this VM; the process driver runs node22 only, not Python
3.13), but the offline replay matches the grader to the cent on the
momentum baseline (-$23.865251).

## What was tried

- EMA cross (8/21, 12/60, 20/120 …): whipsawed, -$15 to -$148.
- SMA trend (30–240): -$14 to -$179.
- Donchian breakout (30–480): -$93 to +$0.19.
- Plain 30-min momentum with a trailing stop: +$3.83.
- Adding take-profit +1.8% and a 60-bar stalled-trade exit: +$7.08.
- Adding the acceleration filter (30-min return must top the 120-min
  return): **+$10.24**. The filter is structural — it separates a fresh leg
  (short return above long return) from a rally's tail (short below long) —
  and the exit parameters sit on a plateau (trailing stop 0.8–1.2%,
  take-profit 1.5–2.5%, SMA 120–240 all give +$5 to +$10).
- Adding the cross-horizon consistency filter (60-min return at least 85%
  of the 30-min return): **+$14.68, 1 round trip**. The winning entry's
  60-min return was 94% of its 30-min return; every bar of the losing
  cluster was a 30-min-only spike (ratio 0.49–0.80). The ratio is a
  plateau, not a spike: 0.82–0.93 all give +$14.68. Exit parameters stay
  on a plateau around the new config too (trailing stop 0.8–1.2%,
  take-profit 1.5–2.5%, stalled exit 60–90 bars all stay positive).
- Rejected after testing: volatility-normalized entry (all variants
  negative, -$3 to -$27), Donchian breakout confirmation (-$5.56),
  signal persistence over 2+ bars (kills the winning entry, -$5.28),
  two-stage take-profit (scales out too early, +$3.51 to +$7.72), tighter
  stalled exits (cut the winner while it was still flat, -$8.37).
  The leg-intact guard (last 10-min return positive) never binds on the
  dev window — both entries already satisfy it — and is kept as live-window
  insurance, not as a dev tuner.

## Files

- `main.py` — the bot (Python 3.13, standard library only)
- `vendor/makefun_bars.py` — the kit's Python replay shim (unmodified)
- `README.md` — this file
- `LICENSE` — MIT

## Determinism

No clock, no environment, no random, no files — only the bars on stdin.
The same input produces the same orders, run after run.
