"""
betting_toolkit.py  -  pure Python 3.8+, no dependencies.

Sections
  1. Odds conversion and implied probability
  2. Removing the bookmaker margin (de-vig): multiplicative, power, Shin
  3. Model probabilities: Poisson + Dixon-Coles scoreline grid (1X2, O/U, BTTS)
  4. Combining model and market probabilities (shrinkage)
  5. Expected value, edge, break-even
  6. Kelly: single bet, push/void bets, exchange commission,
     several simultaneous bets, mutually exclusive outcomes (generic optimiser)
  7. Verification: Brier, log loss, calibration table, CLV, ROI significance
  8. Risk simulation (drawdowns) for a chosen Kelly fraction
  9. recommend_stake(): the full pipeline "noise removed" -> final stake

Run `python betting_toolkit.py` to execute self-tests and demos.
Educational tool. No guarantee of profit. Never stake money you cannot lose.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from itertools import product
from typing import Dict, List, Optional, Sequence, Tuple

# =============================================================================
# 1. ODDS CONVERSION
#    implied probability  q = 1 / d          (decimal odds d)
#    fair odds            d = 1 / p
#    overround (margin)   = sum(1/d_i) - 1   over ALL outcomes of a market
# =============================================================================


def decimal_from_fractional(numerator: float, denominator: float) -> float:
    """5/2 -> 3.5"""
    return 1.0 + numerator / denominator


def decimal_from_american(a: float) -> float:
    """+150 -> 2.5 ; -200 -> 1.5"""
    return 1.0 + a / 100.0 if a > 0 else 1.0 + 100.0 / abs(a)


def implied_prob(d: float) -> float:
    return 1.0 / d


def fair_odds(p: float) -> float:
    return 1.0 / p


def overround(odds: Sequence[float]) -> float:
    """Bookmaker margin of a complete market. 1.47 / 4.80 / 5.20 -> ~0.081"""
    return sum(1.0 / o for o in odds) - 1.0


# =============================================================================
# 2. DE-VIG: turn bookmaker prices into "fair" market probabilities
#    Always pass the odds of EVERY outcome of the market
#    (3 for 1X2, 2 for Over/Under).
# =============================================================================


def devig_multiplicative(odds: Sequence[float]) -> List[float]:
    """p_i = (1/d_i) / sum_j (1/d_j).  Simple; slightly overrates longshots."""
    imp = [1.0 / o for o in odds]
    s = sum(imp)
    return [x / s for x in imp]


def devig_power(odds: Sequence[float]) -> List[float]:
    """p_i = (1/d_i)^k with k chosen so sum p_i = 1. Takes more from longshots."""
    imp = [1.0 / o for o in odds]
    if sum(imp) <= 1.0:
        return devig_multiplicative(odds)
    lo, hi = 1.0, 100.0
    for _ in range(200):
        k = (lo + hi) / 2.0
        if sum(x ** k for x in imp) > 1.0:
            lo = k
        else:
            hi = k
    return [x ** ((lo + hi) / 2.0) for x in imp]


def devig_shin(odds: Sequence[float]) -> List[float]:
    """
    Shin (1993): models a share z of insider money.
      p_i = ( sqrt(z^2 + 4(1-z) q_i^2 / B) - z ) / ( 2(1-z) ),  q_i = 1/d_i, B = sum q
    z solved by bisection so that sum p_i = 1.
    """
    q = [1.0 / o for o in odds]
    B = sum(q)
    if B <= 1.0:
        return devig_multiplicative(odds)

    def probs(z: float) -> List[float]:
        return [(math.sqrt(z * z + 4 * (1 - z) * x * x / B) - z) / (2 * (1 - z)) for x in q]

    lo, hi = 0.0, 0.9
    for _ in range(200):
        z = (lo + hi) / 2.0
        if sum(probs(z)) > 1.0:
            lo = z
        else:
            hi = z
    p = probs((lo + hi) / 2.0)
    s = sum(p)
    return [x / s for x in p]


DEVIG = {"multiplicative": devig_multiplicative, "power": devig_power, "shin": devig_shin}


# =============================================================================
# 3. MODEL PROBABILITIES: Poisson + Dixon-Coles
#    P(i,j) = tau(i,j) * Pois(i; lam) * Pois(j; mu)
#    lam = expected home goals, mu = expected away goals
#    tau corrects 0-0, 1-0, 0-1, 1-1 (rho is usually about -0.03 ... -0.15)
#      tau(0,0)=1-lam*mu*rho  tau(0,1)=1+lam*rho  tau(1,0)=1+mu*rho  tau(1,1)=1-rho
# =============================================================================


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def dc_tau(i: int, j: int, lam: float, mu: float, rho: float) -> float:
    if i == 0 and j == 0:
        return 1.0 - lam * mu * rho
    if i == 0 and j == 1:
        return 1.0 + lam * rho
    if i == 1 and j == 0:
        return 1.0 + mu * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def score_grid(lam: float, mu: float, rho: float = -0.05, max_goals: int = 10) -> List[List[float]]:
    """grid[i][j] = P(home i, away j), normalised to sum to 1. rho=0 -> plain Poisson."""
    g = [[max(0.0, dc_tau(i, j, lam, mu, rho)) * poisson_pmf(i, lam) * poisson_pmf(j, mu)
          for j in range(max_goals + 1)] for i in range(max_goals + 1)]
    s = sum(map(sum, g))
    return [[x / s for x in row] for row in g]


def market_probs(grid: List[List[float]], line: float = 2.5) -> Dict[str, float]:
    n = len(grid)
    home = sum(grid[i][j] for i in range(n) for j in range(n) if i > j)
    draw = sum(grid[i][i] for i in range(n))
    away = sum(grid[i][j] for i in range(n) for j in range(n) if i < j)
    over = sum(grid[i][j] for i in range(n) for j in range(n) if i + j > line)
    btts = sum(grid[i][j] for i in range(1, n) for j in range(1, n))
    return {"home": home, "draw": draw, "away": away,
            "over": over, "under": 1.0 - over, "btts_yes": btts, "btts_no": 1.0 - btts}


# =============================================================================
# 4. COMBINE MODEL AND MARKET
#    p = w * p_model + (1 - w) * p_market_fair
#    w = 0.3-0.5 unless you have backtests proving more.
#    w=1 trusts the model fully; w=0 means you believe the market (=> no edge).
# =============================================================================


def blend(p_model: float, p_market: float, w_model: float = 0.4) -> float:
    return w_model * p_model + (1.0 - w_model) * p_market


# =============================================================================
# 5. EV / EDGE
#    EV per 1 unit staked = p*d - 1
#    break-even probability = 1/d
#    prob. edge = p - 1/d
# =============================================================================


def effective_odds(d: float, commission: float = 0.0) -> float:
    """Betting exchange: commission is charged on net winnings."""
    return 1.0 + (d - 1.0) * (1.0 - commission)


def expected_value(p: float, d: float) -> float:
    return p * d - 1.0


# =============================================================================
# 6. KELLY
# =============================================================================


def kelly_fraction(p: float, d: float) -> float:
    """f* = (p*d - 1) / (d - 1)  = (b*p - q)/b ,  b = d-1.  0 if no edge."""
    b = d - 1.0
    if b <= 0:
        return 0.0
    return max(0.0, (p * d - 1.0) / b)


def kelly_with_push(p_win: float, p_push: float, d: float) -> float:
    """
    Bets that can be voided (draw-no-bet, Asian handicap/total on whole lines).
    Win -> +b, push -> 0, lose -> -1.  f* = (p_win*b - p_lose) / (b * (p_win + p_lose))
    """
    b = d - 1.0
    p_lose = 1.0 - p_win - p_push
    if b <= 0 or p_win + p_lose <= 0:
        return 0.0
    return max(0.0, (p_win * b - p_lose) / (b * (p_win + p_lose)))


def _growth(f: Sequence[float], scen) -> float:
    tot = 0.0
    for p, r in scen:
        w = 1.0 + sum(fi * ri for fi, ri in zip(f, r))
        if w <= 0:
            return -math.inf
        tot += p * math.log(w)
    return tot


def _project_capped_simplex(v: Sequence[float], cap: float) -> List[float]:
    """Euclidean projection onto {x >= 0, sum x <= cap}."""
    x = [max(0.0, a) for a in v]
    if sum(x) <= cap:
        return x
    u = sorted(v, reverse=True)
    css, theta = 0.0, 0.0
    for k, uk in enumerate(u, 1):
        css += uk
        t = (css - cap) / k
        if uk - t > 0:
            theta = t
    return [max(0.0, a - theta) for a in v]


def kelly_optimize(scenarios: Sequence[Tuple[float, Sequence[float]]], n_bets: int,
                   cap: float = 0.25, iters: int = 3000) -> List[float]:
    """
    GENERAL Kelly: maximise sum_s P_s * log(1 + sum_i f_i * R_si)
    scenarios: [(probability, [net return per unit for bet 0..n-1]), ...]
               net return = d-1 if that bet wins, -1 if it loses, 0 if void.
    cap: maximum total fraction of bankroll across all bets.
    Handles any mix of bets (correlated or not), because YOU define the scenarios.
    """
    assert cap < 1.0
    f = [0.0] * n_bets
    g = _growth(f, scenarios)
    step = 1.0
    for _ in range(iters):
        grad = [0.0] * n_bets
        for p, r in scenarios:
            w = 1.0 + sum(fi * ri for fi, ri in zip(f, r))
            for i in range(n_bets):
                grad[i] += p * r[i] / w
        s, moved = step, False
        for _ in range(50):
            cand = _project_capped_simplex([fi + s * gi for fi, gi in zip(f, grad)], cap)
            gc = _growth(cand, scenarios)
            if gc > g + 1e-15:
                f, g, moved, step = cand, gc, True, min(s * 2.0, 20.0)
                break
            s /= 2.0
        if not moved:
            break
    return f


def independent_scenarios(bets: Sequence[Tuple[float, float]]):
    """bets = [(p_i, d_i), ...] that do not influence each other (different matches)."""
    n = len(bets)
    assert n <= 14, "enumeration is 2^n; keep n <= 14"
    out = []
    for combo in product([1, 0], repeat=n):
        prob = 1.0
        rets = []
        for win, (p, d) in zip(combo, bets):
            prob *= p if win else 1.0 - p
            rets.append(d - 1.0 if win else -1.0)
        out.append((prob, rets))
    return out


def exclusive_scenarios(outcomes: Sequence[Tuple[float, float]]):
    """outcomes = [(p_k, d_k)] of ONE market (e.g. 1X2). p_k must sum to 1."""
    n = len(outcomes)
    out = []
    for k, (p, _) in enumerate(outcomes):
        rets = [(outcomes[i][1] - 1.0 if i == k else -1.0) for i in range(n)]
        out.append((p, rets))
    return out


# =============================================================================
# 7. VERIFICATION: is your probability honest? is your edge real?
# =============================================================================


def brier(preds: Sequence[float], outcomes: Sequence[int]) -> float:
    """mean (p - y)^2. Lower is better. Always-0.5 predictor scores 0.25."""
    return sum((p - y) ** 2 for p, y in zip(preds, outcomes)) / len(preds)


def log_loss(preds: Sequence[float], outcomes: Sequence[int]) -> float:
    eps = 1e-12
    return -sum(y * math.log(max(p, eps)) + (1 - y) * math.log(max(1 - p, eps))
                for p, y in zip(preds, outcomes)) / len(preds)


def calibration_table(preds: Sequence[float], outcomes: Sequence[int], bins: int = 5):
    """[(lo, hi, n, avg_predicted, actual_hit_rate)] - the two last numbers should match."""
    rows = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, p in enumerate(preds) if lo <= p < hi or (b == bins - 1 and p == 1.0)]
        if idx:
            rows.append((lo, hi, len(idx),
                         sum(preds[i] for i in idx) / len(idx),
                         sum(outcomes[i] for i in idx) / len(idx)))
    return rows


def clv(odds_taken: float, closing_odds: Sequence[float], index: int,
        method: str = "shin") -> float:
    """
    Closing line value = odds_taken * p_close_fair - 1.
    Positive over hundreds of bets is the best early proof of a real edge.
    closing_odds: closing odds of ALL outcomes in the market.
    """
    p_close = DEVIG[method](closing_odds)[index]
    return odds_taken * p_close - 1.0


def roi_significance(bets: Sequence[Dict]) -> Dict[str, float]:
    """
    bets: [{"odds": 1.9, "won": True}, ...]  (flat 1-unit returns)
    z = mean_return / standard_error.  z > 1.64 ~ 95% one-sided confidence of profit.
    """
    r = [(b["odds"] - 1.0) if b["won"] else -1.0 for b in bets]
    n = len(r)
    m = sum(r) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in r) / (n - 1)) if n > 1 else float("nan")
    se = sd / math.sqrt(n) if n > 1 else float("nan")
    return {"n": n, "roi": m, "std_per_bet": sd, "z": m / se if se else float("nan")}


def bets_needed(true_roi: float, sd_per_bet: float = 1.0, z: float = 1.64) -> int:
    """How many bets before a true ROI of `true_roi` becomes statistically visible."""
    return math.ceil((z * sd_per_bet / true_roi) ** 2)


# =============================================================================
# 8. RISK SIMULATION
# =============================================================================


def simulate(p_true: float, d: float, f: float, n_bets: int = 200, n_sims: int = 4000,
             seed: int = 1) -> Dict[str, float]:
    """
    Bankroll paths when you stake fraction f of CURRENT bankroll each bet and the
    TRUE win probability is p_true. Use p_true < your estimate to stress-test.
    """
    rng = random.Random(seed)
    finals, dds = [], []
    for _ in range(n_sims):
        bk, peak, mdd = 1.0, 1.0, 0.0
        for _ in range(n_bets):
            bk *= (1.0 + f * (d - 1.0)) if rng.random() < p_true else (1.0 - f)
            peak = max(peak, bk)
            mdd = max(mdd, 1.0 - bk / peak)
        finals.append(bk)
        dds.append(mdd)
    finals.sort()
    return {"median_final": finals[n_sims // 2],
            "p05_final": finals[int(0.05 * n_sims)],
            "p95_final": finals[int(0.95 * n_sims)],
            "prob_ends_below_start": sum(x < 1 for x in finals) / n_sims,
            "prob_drawdown_over_30pct": sum(x > 0.30 for x in dds) / n_sims,
            "prob_drawdown_over_50pct": sum(x > 0.50 for x in dds) / n_sims}


# -----------------------------------------------------------------------------
# KELLY CONTROL: how much of full Kelly do you actually stake?
#   full    1.0   maximum growth only if p is EXACT; huge drawdowns. Avoid.
#   half    0.5   aggressive; only with a well-validated model
#   third   1/3
#   quarter 0.25  sensible default for a model-based bettor
#   eighth  0.125 for accumulators / uncertain models
#   tenth   0.1   very cautious, first 200 bets of a new model
# PROFILES bundle (fraction, max stake per bet as share of bankroll).
# -----------------------------------------------------------------------------
KELLY_PRESETS = {"full": 1.0, "half": 0.5, "third": 1 / 3, "quarter": 0.25,
                 "eighth": 0.125, "tenth": 0.1}
PROFILES = {"conservative": (0.10, 0.01), "standard": (0.25, 0.03), "aggressive": (0.50, 0.05)}


def resolve_fraction(x) -> float:
    """Accepts 0.25, 'quarter', '1/4' ..."""
    if isinstance(x, str):
        if x in KELLY_PRESETS:
            return KELLY_PRESETS[x]
        if "/" in x:
            a, b = x.split("/")
            return float(a) / float(b)
        return float(x)
    return float(x)


# =============================================================================
# 9. THE FULL PIPELINE
# =============================================================================


@dataclass
class StakeRecommendation:
    decision: str
    stake: float
    stake_pct: float
    p_model: float
    p_market_fair: Optional[float]
    p_used: float
    implied_raw: float
    breakeven: float
    ev: float
    prob_edge: float
    kelly_full: float
    uncertainty_factor: float
    kelly_after_fraction: float
    notes: List[str] = field(default_factory=list)

    def report(self) -> str:
        pm = f"{self.p_market_fair:.2%}" if self.p_market_fair is not None else "n/a"
        lines = [
            f"Decision            : {self.decision}",
            f"Model p             : {self.p_model:.2%}",
            f"Market fair p       : {pm}   (raw implied {self.implied_raw:.2%} incl. margin)",
            f"p used (blended)    : {self.p_used:.2%}   break-even {self.breakeven:.2%}",
            f"EV per 1 staked     : {self.ev:+.2%}   prob. edge {self.prob_edge:+.2%}",
            f"Full Kelly          : {self.kelly_full:.2%}",
            f"Uncertainty factor  : {self.uncertainty_factor:.2f}",
            f"After fraction/shrink: {self.kelly_after_fraction:.2%}",
            f"FINAL STAKE         : {self.stake:.2f}  ({self.stake_pct:.2%} of bankroll)",
        ]
        lines += [f"  - {n}" for n in self.notes]
        return "\n".join(lines)


def recommend_stake(
    p_model: float,
    odds: float,
    bankroll: float,
    market_odds: Optional[Sequence[float]] = None,
    market_index: int = 0,
    devig_method: str = "shin",
    w_model: float = 0.4,
    base_fraction=0.25,
    se: float = 0.03,
    use_uncertainty_shrink: bool = True,
    max_stake_pct: float = 0.03,
    min_ev: float = 0.02,
    min_stake: float = 0.0,
    commission: float = 0.0,
    profile: Optional[str] = None,
) -> StakeRecommendation:
    """
    Steps (each removes one kind of noise):
      1. de-vig the market           -> p_market_fair
      2. blend with the model        -> p            (shrinks model overconfidence)
      3. EV and edge vs break-even   -> skip if EV < min_ev
      4. full Kelly                  -> f*
      5. x base_fraction (0.25 = quarter Kelly)
      6. x edge^2 / (edge^2 + se^2)  -> shrinks stakes when edge is small relative
                                         to the error of your probability (se)
      7. cap at max_stake_pct, apply min stake, round
    odds: the price you can actually get on the selection.
    market_odds: odds of ALL outcomes in that market at (ideally) the same bookmaker.
    se: honest standard error of your probability, e.g. 0.03 = +/-3 points.
    """
    notes: List[str] = []
    if profile is not None:                      # 'conservative' | 'standard' | 'aggressive'
        base_fraction, max_stake_pct = PROFILES[profile]
    base_fraction = resolve_fraction(base_fraction)   # 0.25, 'quarter', '1/4' all work
    d_eff = effective_odds(odds, commission)
    breakeven = 1.0 / d_eff

    if market_odds is not None:
        p_mkt = DEVIG[devig_method](market_odds)[market_index]
        p = blend(p_model, p_mkt, w_model)
        implied_raw = 1.0 / market_odds[market_index]
        notes.append(f"Bookmaker margin in this market: {overround(market_odds):.2%}")
    else:
        p_mkt, p, implied_raw = None, p_model, 1.0 / odds
        notes.append("No market odds supplied: model probability used un-blended (risky).")

    ev = expected_value(p, d_eff)
    edge = p - breakeven
    f_full = kelly_fraction(p, d_eff)

    if use_uncertainty_shrink and edge > 0:
        unc = edge ** 2 / (edge ** 2 + se ** 2)
    else:
        unc = 1.0 if edge > 0 else 0.0
    f_adj = f_full * base_fraction * unc
    f_final = min(f_adj, max_stake_pct)
    if f_adj > max_stake_pct:
        notes.append(f"Capped at {max_stake_pct:.1%} of bankroll.")

    decision = "BET"
    if ev < min_ev:
        decision = "PASS"
        f_final = 0.0
        notes.append(f"EV {ev:+.2%} is below the required minimum {min_ev:.1%}.")
    stake = round(bankroll * f_final, 2)
    if decision == "BET" and stake < min_stake:
        decision, stake, f_final = "PASS", 0.0, 0.0
        notes.append("Stake below minimum bet size.")

    return StakeRecommendation(decision, stake, f_final, p_model, p_mkt, p, implied_raw,
                               breakeven, ev, edge, f_full, unc, f_adj, notes)


# =============================================================================
# 10. ACCUMULATORS (several selections on ONE bet)
#   combined odds        D = d1 * d2 * ... * dn
#   combined probability P = p1 * p2 * ... * pn        (independent matches only)
#   margin compounds:    (1+m1)(1+m2)... - 1           (5% x 4 legs ~ 21.6%)
#   error compounds:     se_P ~ P * sqrt( sum (se_i / p_i)^2 )   (delta method)
# Same-game legs are CORRELATED (e.g. "Viking win" and "Over 2.5"): never multiply
# them; use a joint probability from the scoreline grid (grid_prob) and the
# bookmaker's own same-game price (combined_odds=).
# =============================================================================


def grid_prob(grid: List[List[float]], predicate) -> float:
    """P(event) from a scoreline grid. predicate(i, j) -> bool, i=home goals, j=away goals.
    e.g. home win AND over 2.5:  lambda i, j: i > j and i + j > 2.5"""
    n = len(grid)
    return sum(grid[i][j] for i in range(n) for j in range(n) if predicate(i, j))


def fit_lambdas(p_home: float, p_over: float, line: float = 2.5, rho: float = -0.05):
    """Find expected goals (lam, mu) whose grid reproduces a site's P(home win) and
    P(over line). Lets you build consistent same-game joint probabilities."""
    def err(l, m):
        mp = market_probs(score_grid(l, m, rho, max_goals=9), line)
        return (mp["home"] - p_home) ** 2 + (mp["over"] - p_over) ** 2

    best = (9e9, 1.5, 1.2)
    lo_l, hi_l, lo_m, hi_m = 0.2, 4.5, 0.1, 3.5
    steps = 14
    for _ in range(4):
        for a in range(steps + 1):
            l = lo_l + (hi_l - lo_l) * a / steps
            for b in range(steps + 1):
                m = lo_m + (hi_m - lo_m) * b / steps
                e = err(l, m)
                if e < best[0]:
                    best = (e, l, m)
        wl, wm = (hi_l - lo_l) / steps * 2, (hi_m - lo_m) / steps * 2
        lo_l, hi_l = max(0.05, best[1] - wl), best[1] + wl
        lo_m, hi_m = max(0.05, best[2] - wm), best[2] + wm
    return best[1], best[2]


@dataclass
class Leg:
    name: str
    p_model: float
    odds: float
    market_odds: Optional[Sequence[float]] = None   # ALL outcomes of that leg's market
    market_index: int = 0


def recommend_accumulator(
    legs: Sequence[Leg],
    bankroll: float,
    se_leg: float = 0.03,
    w_model: float = 0.4,
    devig_method: str = "shin",
    base_fraction="eighth",
    max_stake_pct: float = 0.01,
    min_ev: float = 0.03,
    combined_odds: Optional[float] = None,
    joint_model_p: Optional[float] = None,
    sgp_margin: float = 0.10,
    profile: Optional[str] = None,
) -> StakeRecommendation:
    """
    Independent legs: leave combined_odds / joint_model_p as None.
    Same-game legs : pass the bookmaker's same-game price as combined_odds and the
                     model's joint probability (from grid_prob) as joint_model_p.
                     sgp_margin = assumed bookmaker margin on that combined price.
    Stricter defaults than singles: eighth Kelly, 1% cap, 3% minimum EV.
    """
    if profile is not None:
        base_fraction, max_stake_pct = PROFILES[profile]
    base_fraction = resolve_fraction(base_fraction)
    notes: List[str] = []
    ps, fair, singles, margin = [], [], [], 1.0
    for lg in legs:
        if lg.market_odds is not None:
            pm = DEVIG[devig_method](lg.market_odds)[lg.market_index]
            p = blend(lg.p_model, pm, w_model)
            margin *= 1.0 + overround(lg.market_odds)
        else:
            pm, p = lg.p_model, lg.p_model
            notes.append(f"{lg.name}: no market odds, model p used un-blended.")
        ps.append(p)
        fair.append(pm)
        ev1 = p * lg.odds - 1.0
        singles.append(ev1)
        notes.append(f"leg {lg.name}: p_used {p:.1%} @ {lg.odds:.2f} -> single EV {ev1:+.1%}")

    prod_odds = 1.0
    for lg in legs:
        prod_odds *= lg.odds
    D = combined_odds if combined_odds is not None else prod_odds

    if joint_model_p is not None:
        assert combined_odds is not None, "same-game: give the bookmaker's combined odds"
        p_mkt_joint = (1.0 / combined_odds) / (1.0 + sgp_margin)
        P = blend(joint_model_p, p_mkt_joint, w_model)
        p_fair_c = p_mkt_joint
        notes.append(f"Same-game joint: model {joint_model_p:.1%}, market-implied {p_mkt_joint:.1%}")
    else:
        P = 1.0
        p_fair_c = 1.0
        for p, f in zip(ps, fair):
            P *= p
            p_fair_c *= f
        notes.append(f"Compounded bookmaker margin over {len(legs)} legs: {margin - 1:.1%}")

    se_c = P * math.sqrt(sum((se_leg / p) ** 2 for p in ps))
    ev = P * D - 1.0
    edge = P - 1.0 / D
    f_full = kelly_fraction(P, D)
    unc = edge ** 2 / (edge ** 2 + se_c ** 2) if edge > 0 else 0.0
    f_adj = f_full * base_fraction * unc
    f_final = min(f_adj, max_stake_pct)
    decision = "BET"
    if ev < min_ev:
        decision, f_final = "PASS", 0.0
        notes.append(f"Accumulator EV {ev:+.2%} below required {min_ev:.1%}.")
    best_single = max(singles)
    if ev < best_single:
        notes.append(f"Best single leg has higher EV ({best_single:+.1%}) than the accumulator "
                     f"({ev:+.1%}): singles are the better way to bet this.")
    notes.append(f"Combined odds {D:.2f}, combined p {P:.2%} (+/-{se_c:.1%}), win chance 1 in {1 / P:.1f}")
    return StakeRecommendation(decision, round(bankroll * f_final, 2), f_final,
                               joint_model_p if joint_model_p is not None else
                               math.prod(l.p_model for l in legs),
                               p_fair_c, P, 1.0 / D, 1.0 / D, ev, edge, f_full, unc, f_adj, notes)


# =============================================================================
# SELF-TESTS AND DEMOS
# =============================================================================


def _self_tests() -> None:
    assert abs(kelly_fraction(0.56, 2.0) - 0.12) < 1e-12
    assert kelly_fraction(0.40, 2.0) == 0.0
    assert abs(sum(devig_multiplicative([1.47, 4.8, 5.2])) - 1) < 1e-9
    assert abs(sum(devig_power([1.47, 4.8, 5.2])) - 1) < 1e-9
    assert abs(sum(devig_shin([1.47, 4.8, 5.2])) - 1) < 1e-9
    g = score_grid(1.5, 1.1, -0.05)
    assert abs(sum(map(sum, g)) - 1) < 1e-9
    m = market_probs(g)
    assert abs(m["home"] + m["draw"] + m["away"] - 1) < 1e-9
    # optimiser must reproduce the closed form for a single bet
    f = kelly_optimize(independent_scenarios([(0.56, 2.0)]), 1, cap=0.9)[0]
    assert abs(f - 0.12) < 1e-3, f
    # push formula must reduce to normal Kelly when p_push = 0
    assert abs(kelly_with_push(0.56, 0.0, 2.0) - 0.12) < 1e-12
    assert resolve_fraction("quarter") == 0.25 and resolve_fraction("1/4") == 0.25
    gr = score_grid(1.8, 1.2, -0.05)
    assert abs(grid_prob(gr, lambda i, j: i > j) - market_probs(gr)["home"]) < 1e-12
    l, m = fit_lambdas(0.60, 0.55)
    mp = market_probs(score_grid(l, m, -0.05, 9))
    assert abs(mp["home"] - 0.60) < 0.01 and abs(mp["over"] - 0.55) < 0.01
    print("self-tests passed\n")


def _demo() -> None:
    print("=== 1. Odds, margin and de-vig (placeholder 1X2 odds, use real ones) ===")
    odds_1x2 = [1.47, 4.80, 5.20]
    print("raw implied:", [round(1 / o, 4) for o in odds_1x2], " margin:", f"{overround(odds_1x2):.2%}")
    for name, fn in DEVIG.items():
        print(f"{name:15s}", [round(x, 4) for x in fn(odds_1x2)])

    print("\n=== 2. Model probability from expected goals (Dixon-Coles) ===")
    mp = market_probs(score_grid(2.96, 1.33, rho=-0.05))
    print({k: round(v, 4) for k, v in mp.items()})

    print("\n=== 3. Full pipeline: Viking win @1.47, model 68.64% ===")
    r = recommend_stake(0.6864, 1.47, bankroll=1000, market_odds=odds_1x2, market_index=0)
    print(r.report())

    print("\n=== 4. Pipeline with genuine value: Over 2.5 @2.10, Under @1.80, model 60% ===")
    r = recommend_stake(0.60, 2.10, bankroll=1000, market_odds=[2.10, 1.80], market_index=0)
    print(r.report())

    print("\n=== 5. Special cases ===")
    print("Draw-no-bet (win .42, push .26, lose .32) @1.85 ->",
          f"{kelly_with_push(0.42, 0.26, 1.85):.2%}")
    print("Exchange, 2% commission, p .56 @2.0 ->",
          f"{kelly_fraction(0.56, effective_odds(2.0, 0.02)):.2%}")
    bets = [(0.56, 2.0), (0.55, 1.95), (0.60, 1.80)]
    f = kelly_optimize(independent_scenarios(bets), 3, cap=0.25)
    print("3 simultaneous independent bets, full Kelly:", [f"{x:.2%}" for x in f],
          " (single-bet Kelly would be", [f"{kelly_fraction(p, d):.2%}" for p, d in bets], ")")
    ex = [(0.62, 1.75), (0.22, 3.90), (0.16, 5.00)]   # model p, bookmaker odds (home/draw/away)
    f = kelly_optimize(exclusive_scenarios(ex), 3, cap=0.5)
    print("1X2 (home/draw/away) full Kelly, only +EV outcomes get stake:", [f"{x:.2%}" for x in f])

    print("\n=== 6. Why fractional Kelly: simulation, true p is 2 points below estimate ===")
    p_est, d = 0.56, 2.0
    for frac in (1.0, 0.5, 0.25):
        s = simulate(p_est - 0.02, d, kelly_fraction(p_est, d) * frac, n_bets=200)
        print(f"{frac:>4} Kelly | median end {s['median_final']:.2f}x | 5th pct {s['p05_final']:.2f}x"
              f" | P(end<start) {s['prob_ends_below_start']:.0%}"
              f" | P(drawdown>50%) {s['prob_drawdown_over_50pct']:.0%}")

    print("\n=== 7. Verification ===")
    preds = [0.7, 0.65, 0.6, 0.55, 0.8, 0.3, 0.45, 0.72, 0.58, 0.62]
    outs = [1, 1, 0, 1, 1, 0, 0, 1, 0, 1]
    print("Brier:", round(brier(preds, outs), 4), " log loss:", round(log_loss(preds, outs), 4))
    for row in calibration_table(preds, outs, 5):
        print("bin %.1f-%.1f n=%d predicted %.2f actual %.2f" % row)
    print("CLV (took 1.47, closing 1.40/5.0/5.6):", f"{clv(1.47, [1.40, 5.0, 5.6], 0):+.2%}")
    print("Bets needed to see a 2% true ROI:", bets_needed(0.02), "(~1.64 sigma, sd~1/bet)")


if __name__ == "__main__":
    _self_tests()
    _demo()