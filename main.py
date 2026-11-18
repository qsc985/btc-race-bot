"""Leg-rider momentum bot for btc-race-24h-20261118-1444 (agent-fun/bars-replay/v1).

Strategy: ride strong short-term up-legs in cbBTC, long only, one position at a time.
  Entry (flat): the 30-minute return tops +0.5% AND tops the 120-minute return (the move
    is accelerating, not the tail of a spent rally) AND the close sits above its 120-minute
    simple moving average (uptrend context). Buys with all cash.
  Exit (long): first of take-profit +1.8% from entry, a 0.8% trailing stop below the best
    close since entry, the close falling under its 120-minute SMA, or 60 bars held with
    less than +0.3% (a stalled trade). After any exit, a 30-bar cooldown before re-entry.

Why this shape: 1-minute BTC bars are mostly noise (per-minute sigma ~0.07%), while a full
round trip costs ~26 bps in fee + slippage + impact, so the bot only trades when a move is
already large enough to pay for itself, and it gets out fast when the move stalls. On the
frozen 24h dev window it nets +$10.24 on $1,000 (4 trades, max drawdown 0.65%).

Deterministic: no clock, no environment, no random, no files — only the bars on stdin.
Standard library only. Run by the grader as `python3 -P -s /bot/main.py`.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

# --- parameters (tuned on the dev window; see README for the sweep) ---
RET_N = 30            # short return window, minutes
RET_THR = 0.005       # short return must top +0.5%
ACC_N = 120           # long return window, minutes (must be topped: accelerating)
SMA_N = 120           # trend context: close must sit above its SMA
TRAIL = 0.008         # trailing stop: 0.8% below the best close since entry
TAKE_PROFIT = 0.018   # take profit: +1.8% from the entry close
TIME_EXIT = 60        # stalled-trade exit: this many bars held ...
TIME_MIN_RET = 0.003  # ... with less than +0.3% from entry
COOLDOWN = 30         # bars to wait after an exit before re-entering
MAX_SLIPPAGE_BPS = 10000  # wide open: never let a fill be refused on slippage
MIN_NOTIONAL = 1000000    # 1 USDC, the harness minimum for a buy


class Bot:
    def __init__(self):
        self.symbol = None
        self.closes = []        # closes seen, ints (price_scale units), oldest first
        self.peak = None        # best close since entry
        self.entry_px = None    # close at the entry decision
        self.entry_k = None     # bar index of the entry decision
        self.cool_until = -1    # no entries at or before this bar index

    def _sma(self, n):
        return sum(self.closes[-n:]) / n

    def on_batch(self, state, batch):
        if self.symbol is None:
            self.symbol = state.hello["symbols"][0]["symbol"]
        if state.warming_up:
            return []
        close = state.close(self.symbol)
        if close is None:
            return []
        self.closes.append(close)
        k = len(self.closes) - 1
        pos = state.positions.get(self.symbol)
        qty = pos.qty if pos is not None else 0

        if qty > 0:
            return self._exit(state, k, close, qty)
        return self._enter(state, k, close)

    def _exit(self, state, k, close, qty):
        if self.peak is None or self.entry_px is None:
            # Position without entry bookkeeping (should not happen): hold it.
            self.peak = close
            self.entry_px = close
            self.entry_k = k
        if close > self.peak:
            self.peak = close
        reason = None
        if close >= self.entry_px * (1 + TAKE_PROFIT):
            reason = "take-profit"
        elif close < self.peak * (1 - TRAIL):
            reason = "trailing-stop"
        elif k >= SMA_N and close < self._sma(SMA_N):
            reason = "below-sma"
        elif (self.entry_k is not None and k - self.entry_k >= TIME_EXIT
                and close < self.entry_px * (1 + TIME_MIN_RET)):
            reason = "stalled"
        if reason is None:
            return []
        self.cool_until = k + COOLDOWN
        self.peak = None
        self.entry_px = None
        self.entry_k = None
        return [{"side": "sell", "symbol": self.symbol, "qty": qty,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]

    def _enter(self, state, k, close):
        if k < max(RET_N, ACC_N, SMA_N) or k <= self.cool_until:
            return []
        r_short = close / self.closes[k - RET_N] - 1
        if r_short < RET_THR:
            return []
        r_long = close / self.closes[k - ACC_N] - 1
        if r_short <= r_long:
            return []  # move is decelerating, not accelerating
        if close <= self._sma(SMA_N):
            return []  # no uptrend context
        if state.cash < MIN_NOTIONAL:
            return []
        self.peak = close
        self.entry_px = close
        self.entry_k = k
        return [{"side": "buy", "symbol": self.symbol,
                 "notional_quote_units": state.cash,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]


makefun_bars.run(Bot().on_batch)
