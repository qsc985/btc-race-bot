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
  close sits above its 120-minute SMA (uptrend context). Buys with all cash.
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
| Net PnL | **+$10.24** (on $1,000) |
| Trades | 4 (2 round trips) |
| Max drawdown | 0.65% |
| Fees paid | $1.62 |

Trade log: buy $64,069 → sell $65,062 (the mid-window rally); buy $64,760 →
sell $64,528 (a late small rally, cut by the stalled-trade exit). Verified with
the kit's local grader (`makefun grade-local --driver process`), which
reproduces the server's dev grading; an independent offline replay of the
harness fill math matches the grader to the cent on the momentum baseline
(-$23.865251).

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

## Files

- `main.py` — the bot (Python 3.13, standard library only)
- `vendor/makefun_bars.py` — the kit's Python replay shim (unmodified)
- `README.md` — this file
- `LICENSE` — MIT

## Determinism

No clock, no environment, no random, no files — only the bars on stdin.
The same input produces the same orders, run after run.
