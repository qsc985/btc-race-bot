"""Leg-rider momentum bot for btc-race-24h-20261118-1444 (agent-fun/bars-replay/v1).

Long only, one position at a time, full size, trading cbBTC on 1-minute bars.

Entry (flat) — five guards, all must pass:
  1. Momentum: the 30-minute return tops +0.5%.
  2. Acceleration: the 30-minute return tops the 120-minute return, so the
     move is speeding up rather than the tail of a spent rally.
  3. Cross-horizon consistency: the 60-minute return is at least 85% of the
     30-minute return. A real up-leg shows up across horizons; a spike
     confined to the last 30 minutes is usually a blip that mean-reverts
     before it pays the ~26 bps round-trip cost. On the dev window this
     filter drops the one false entry (a 30-min spike whose 60-min return
     was only half as strong) while keeping the genuine leg.
  4. Trend context: the close sits above its 120-minute SMA.
  5. Leg intact: the last 10 minutes are still positive. Guards against
     entering on a 30-minute return whose most recent price action has
     already rolled over — the signal fires on history, the trade lives
     in the present. On the dev window this guard never binds (both
     entries already satisfy it), so the dev result is unchanged; it is
     there for the live window, where a rolled-over leg is the most
     common way a momentum entry starts underwater.

Exit (long), first trigger wins: take-profit +1.8% from entry, a 0.8%
trailing stop below the best close since entry, the close falling under its
120-minute SMA, or 60 bars held with less than +0.3% (a stalled trade).
After any exit, a 30-bar cooldown before re-entering.

Dev-window result (frozen 24h, 1,440 bars): net PnL +$14.68 on $1,000,
1 round trip, max drawdown 0.64%. The previous version without guard 3
netted +$10.24 across 2 round trips; the dropped trade was the false
30-minute spike, exited by the stalled-trade rule at -0.13%.

Deterministic: no clock, no environment, no random, no files — only the
bars on stdin. Standard library only. Run by the grader as
`python3 -P -s /bot/main.py`.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

# --- parameters ---
SHORT_N = 30          # short return window, minutes
SHORT_THR = 0.005     # short return must top +0.5%
LONG_N = 120          # long return window, minutes (must be topped: accelerating)
MID_N = 60            # mid return window, minutes (consistency check)
MID_RATIO = 0.85      # mid return must be at least 85% of the short return
LEG_N = 10            # leg-intact window, minutes: last 10-min return must be > 0
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

    def _ret(self, n, k):
        """Return over the last n minutes ending at bar k."""
        return self.closes[k] / self.closes[k - n] - 1

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
        if k < max(SHORT_N, LONG_N, MID_N, SMA_N) or k <= self.cool_until:
            return []
        r_short = self._ret(SHORT_N, k)
        if r_short < SHORT_THR:
            return []  # no momentum
        if r_short <= self._ret(LONG_N, k):
            return []  # move is decelerating, not accelerating
        if self._ret(MID_N, k) < MID_RATIO * r_short:
            return []  # spike confined to the last 30 minutes, not a broad leg
        if self._ret(LEG_N, k) < 0:
            return []  # leg already rolling over in the last 10 minutes
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
