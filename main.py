"""
main.py - single-match value check and stake calculator.

    1. Put this file in the same folder as betting_toolkit.py
    2. Edit ONLY section 1 (INPUTS) and, if you want, section 2 (SETTINGS)
    3. Run:  python main.py
    4. Read the VERDICT lines at the end. PASS = do not bet at this price.

The script (a) validates your inputs, (b) removes the bookmaker margin, (c) blends model
and market, (d) decides BET/PASS, (e) sizes the stake with fractional Kelly, and
(f) shows the price you would need and how sensitive the answer is.

Educational tool. It cannot make a losing price profitable. Never stake money you
cannot afford to lose.
"""
import math
import sys

from betting_toolkit import (DEVIG, PROFILES, Leg, fit_lambdas, grid_prob, market_probs,
                             overround, recommend_accumulator, recommend_stake,
                             resolve_fraction, score_grid, kelly_fraction)
from betlog import export_to_matches, log_recommendation

# =============================================================================
# 1. INPUTS  (edit these)
# =============================================================================

# --- The match ---------------------------------------------------------------
# VERIFY: teams, date and kick-off on the ForzaPitch page AND on your bookmaker's coupon
# must be the same fixture (check it is not a different league or a youth/reserve match).
MATCH = "Hoffenheim - Leverkusen - Bundesliga - 2026-10-25"

# --- Your money --------------------------------------------------------------
# BANKROLL: money reserved ONLY for betting that you can afford to lose entirely.
#   Use the CURRENT balance (after open bets), update it before every session.
BANKROLL = 15.0
# MIN_BET: the smallest stake your bookmaker accepts (look in the bet slip / rules).
#   With a small bankroll the correct Kelly stake can be BELOW this -> then it is a PASS,
#   do not round up to the minimum (that over-bets your edge).
MIN_BET = 1.0

# --- Model probabilities (ForzaPitch page, block "Pre-match analysis" / "Market probabilities") ---
# VERIFY: the three 1X2 numbers must add to ~100%; the match header (teams/date) must match.
#   Sanity-check the model before trusting it:
#     * Is the sample reasonable? (page shows accuracy "62.5% on 40 predictions" - small sample)
#     * Do form/table agree? (league positions, "Season stats" and "Venue form" blocks)
#     * Does the page's xG agree with its own goals stats? (total xG vs goals per game)
#     * Any key injury/suspension/rotation the model cannot know? (Flashscore, Transfermarkt,
#       club press conference) -> if yes, lower the probability or skip.
MODEL_1X2 = {"home": 0.3481, "draw": 0.2995, "away": 0.3524}
# Over 2.5: the page's "Over 2.5" probability (shown rounded, e.g. 60%). Under 2.5 = 1 - Over 2.5.
MODEL_OVER25 = 0.60

# --- Bookmaker odds (DECIMAL odds, same bookmaker, same moment) --------------
# Enter ALL outcomes of each market, in this exact order. The margin removal needs them all.
#   1X2 market must be "Full time result / 90 minutes" (NOT draw-no-bet, NOT double chance).
#   VERIFY: take a screenshot or note the time; prices move. Re-enter just before betting.
ODDS_1X2 = [3.15, 3.75, 1.93]      # [home win, draw, away win]
#   Over/Under market must be the 2.5 line, order [over, under].
ODDS_OU25 = [1.28, 3.30]           # [over 2.5, under 2.5]

# --- Which bets to evaluate ---------------------------------------------------
# "p_model"      : model probability for THIS selection
# "market_odds"  : the odds list of that market (from above)
# "index"        : position of the selection in that list (0 = first entry)
# The price you get is market_odds[index] - it is taken from the list automatically, so
# you can never enter the price and the market inconsistently.
BETS = [
    {"name": "Hoffenheim win",  "p_model": MODEL_1X2["home"], "market_odds": ODDS_1X2,  "index": 0},
    {"name": "Draw",            "p_model": MODEL_1X2["draw"], "market_odds": ODDS_1X2,  "index": 1},
    {"name": "Leverkusen win",  "p_model": MODEL_1X2["away"], "market_odds": ODDS_1X2,  "index": 2},
    {"name": "Over 2.5 goals",  "p_model": MODEL_OVER25,      "market_odds": ODDS_OU25, "index": 0},
    {"name": "Under 2.5 goals", "p_model": 1 - MODEL_OVER25, "market_odds": ODDS_OU25, "index": 1},
]

# --- Optional: same-game combination (HOME win AND Over 2.5 in one bet) -------
# Put the bookmaker's quoted price for the combination here, or leave None to skip.
# VERIFY: the price must be the bookmaker's own "bet builder / same-game" price.
SAME_GAME_ODDS = None   # e.g. 1.90

# --- Optional: REQUIREMENTS CHECK for any odds + wager ------------------------
# "What must be true for THIS wager at THESE odds to be worth it, under my Kelly settings?"
# Works for a single bet or an accumulator's TOTAL coefficient (product of leg odds).
# Leave all three as None to skip. (A requirements block at your MIN_BET is always printed
# for each bet above.)
REQ_ODDS = None    # total coefficient / decimal odds, e.g. 6.49
REQ_WAGER = None   # the stake you are considering, e.g. 2.00
REQ_P = None       # your best estimate of the win probability (0-1), optional.
#                    For an accumulator use the combined p from check_accumulator.py and set
#                    PROFILE = "conservative" (accumulators deserve the stricter settings).

# =============================================================================
# 2. SETTINGS  (sensible defaults; change only with a reason)
# =============================================================================
# PROFILE: 'conservative' (1/10 Kelly, 1% cap) | 'standard' (1/4 Kelly, 3% cap)
#          | 'aggressive' (1/2 Kelly, 5% cap). Set None to use BASE_FRACTION / MAX_STAKE_PCT.
PROFILE = "standard"
BASE_FRACTION = "quarter"   # 'full','half','third','quarter','eighth','tenth' or a number
MAX_STAKE_PCT = 0.03        # largest stake as share of bankroll (used when PROFILE=None)
# W_MODEL: trust in the model vs the market. 0.4 = 40% model / 60% market.
#   Raise (0.6-0.8) ONLY after 200+ logged bets show the model is calibrated.
W_MODEL = 0.4
# SE: your honest error on the probability (0.03 = +/-3 points). Bigger SE = smaller stakes.
SE = 0.03
# MIN_EV: skip bets whose expected value is below this (2% protects against model noise).
MIN_EV = 0.02
DEVIG_METHOD = "shin"       # 'shin' | 'power' | 'multiplicative'
COMMISSION = 0.0            # betting exchange commission, e.g. 0.02. Bookmaker: 0.

# --- Target profit: "what stake do I need to win X if the bet wins?" ----------
# Prints, for every bet, the stake needed to make this profit IF IT WINS, and what that
# stake means (share of bankroll, expected loss when EV is negative). Set None to hide.
TARGET_PROFIT = 1.00

# --- Logging and accumulator hand-off ----------------------------------------
# LOG_RECOMMENDATIONS: save every BET and PASS to bets_log.csv (settle later with
#   `python betlog.py settle`, review with `python betlog.py report`).
# EXPORT_FOR_ACCUMULATORS: copy each selection to matches.csv so you can combine singles
#   from different matches with check_accumulator.py / accumulator_scanner.py.
LOG_RECOMMENDATIONS = True
LOG_FILE = "bets_log.csv"
EXPORT_FOR_ACCUMULATORS = True
MATCHES_CSV = "matches.csv"

# =============================================================================
# 3. VALIDATION - catches typos before they cost money
# =============================================================================

if PROFILE:
    FRACTION, CAP = PROFILES[PROFILE]
else:
    FRACTION, CAP = resolve_fraction(BASE_FRACTION), MAX_STAKE_PCT


def validate():
    errors, warns = [], []
    if BANKROLL <= 0:
        errors.append("BANKROLL must be positive.")
    s = sum(MODEL_1X2.values())
    if abs(s - 1) > 0.015:
        errors.append(f"MODEL_1X2 sums to {s:.1%}; it should be ~100%. Re-copy from the page.")
    for nm, p in list(MODEL_1X2.items()) + [("over2.5", MODEL_OVER25)]:
        if not 0 < p < 1:
            errors.append(f"Probability '{nm}' = {p} must be between 0 and 1 (use 0.68, not 68).")
    for label, odds, n in [("ODDS_1X2", ODDS_1X2, 3), ("ODDS_OU25", ODDS_OU25, 2)]:
        if len(odds) != n:
            errors.append(f"{label} needs {n} prices, you gave {len(odds)}.")
            continue
        if any(o <= 1.0 for o in odds):
            errors.append(f"{label}: decimal odds must be > 1.0 (e.g. 1.47).")
            continue
        m = overround(odds)
        if m < 0:
            errors.append(f"{label}: margin is {m:.1%} (negative). That is an arbitrage or a typo.")
        elif m < 0.01:
            warns.append(f"{label}: margin only {m:.1%} - unusually low, double-check the prices.")
        elif m > 0.12:
            warns.append(f"{label}: margin {m:.1%} is high - check you entered the right market.")
    for b in BETS:
        if not 0 <= b["index"] < len(b["market_odds"]):
            errors.append(f"{b['name']}: index {b['index']} is outside its odds list.")
    if not errors:
        for b in BETS:
            fair = DEVIG[DEVIG_METHOD](b["market_odds"])[b["index"]]
            if abs(b["p_model"] - fair) > 0.12:
                warns.append(f"{b['name']}: model {b['p_model']:.1%} vs market {fair:.1%} differ by "
                             f"> 12 points. Check: (1) inputs copied right and same fixture/date, "
                             f"(2) odds are current, (3) team news. If all fine, the model is most "
                             f"likely missing information: trust the market, not the model.")
    if REQ_ODDS is not None or REQ_WAGER is not None:
        if REQ_ODDS is None or REQ_WAGER is None:
            errors.append("REQ_ODDS and REQ_WAGER must both be set (or both None).")
        else:
            if REQ_ODDS <= 1.0:
                errors.append("REQ_ODDS must be > 1.0 (decimal odds).")
            if REQ_WAGER <= 0:
                errors.append("REQ_WAGER must be positive.")
    if REQ_P is not None and not 0 < REQ_P < 1:
        errors.append("REQ_P must be between 0 and 1 (use 0.31, not 31).")
    if TARGET_PROFIT is not None and TARGET_PROFIT <= 0:
        errors.append("TARGET_PROFIT must be positive (or None).")
    if BANKROLL * CAP < MIN_BET:
        warns.append(f"Your maximum stake ({BANKROLL * CAP:.2f}) is below MIN_BET ({MIN_BET:.2f}): "
                     f"with this bankroll no bet will be possible under the cap.")
    return errors, warns


# =============================================================================
# 4. ANALYSIS
# =============================================================================

def stake_at(p, price):
    """Stake the pipeline would give at another price, holding p fixed."""
    ev, edge = p * price - 1.0, p - 1.0 / price
    if ev < MIN_EV or edge <= 0:
        return ev, 0.0
    f = kelly_fraction(p, price) * FRACTION * (edge ** 2 / (edge ** 2 + SE ** 2))
    return ev, min(f, CAP) * BANKROLL


def stake_share(p, price):
    """Share of bankroll the configured pipeline would stake at this p and price."""
    ev, edge = p * price - 1.0, p - 1.0 / price
    if ev < MIN_EV or edge <= 0:
        return 0.0
    f = kelly_fraction(p, price) * FRACTION * (edge ** 2 / (edge ** 2 + SE ** 2))
    return min(f, CAP)


def _bisect(fn, lo, hi, target, iters=80):
    """Smallest x in [lo, hi] with fn(x) >= target (fn non-decreasing); None if impossible."""
    if fn(hi) < target:
        return None
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        if fn(mid) >= target:
            hi = mid
        else:
            lo = mid
    return hi


def requirements(odds, wager, p=None, title="REQUIREMENTS CHECK"):
    """
    What must be true for `wager` at `odds` to be worth it, under your Kelly settings.
      * break-even probability            = 1 / odds                    (EV = 0)
      * probability for EV >= MIN_EV      = (1 + MIN_EV) / odds
      * probability that JUSTIFIES the wager = smallest p for which the configured
        Kelly stake (fraction, uncertainty shrink, cap) is at least `wager`
      * if p is given: EV, expected profit in money, allowed stake, minimum odds,
        minimum bankroll
    """
    be, cap_money = 1.0 / odds, CAP * BANKROLL
    print(f"\n  {title}: odds {odds:.2f}, wager {wager:.2f}, bankroll {BANKROLL:.2f}")
    print(f"   - If it wins you gain {wager * (odds - 1):.2f}; if it loses you lose {wager:.2f}.")
    print(f"   - Break-even win probability (EV = 0)       : {be:.1%}")
    print(f"   - Needed for EV >= {MIN_EV:.0%}                      : {(1 + MIN_EV) / odds:.1%}")
    if wager > cap_money:
        print(f"   - Your wager is above the Kelly cap ({CAP:.0%} of bankroll = {cap_money:.2f}): "
              f"it can never be justified under these settings.")
    else:
        pj = _bisect(lambda x: stake_share(x, odds) * BANKROLL, min(be + 1e-6, 0.9999), 0.9999, wager)
        if pj is None:
            print("   - No realistic win probability justifies this wager under your settings.")
        else:
            print(f"   - Win probability that JUSTIFIES this wager      : {pj:.1%} "
                  f"({(pj - be) * 100:+.1f} points above break-even)")
            print("     (Ask yourself honestly whether the true probability is at least this high.)")
    if p is None:
        return
    ev = p * odds - 1.0
    share = stake_share(p, odds)
    allowed = share * BANKROLL
    print(f"   With your probability p = {p:.1%}:")
    print(f"   - EV {ev:+.2%}; expected profit on this wager {wager * ev:+.3f}")
    print(f"   - Stake allowed by your Kelly settings: {allowed:.2f} "
          f"({share:.2%} of bankroll)")
    if allowed <= 0:
        print("   - Your settings say NO BET at this p and price.")
    elif wager > allowed * 1.0001:
        print(f"   - Your wager is {wager / allowed:.1f}x larger than the configured stake: over-betting.")
    else:
        print("   - Your wager is within the configured stake.")
    mo_ev = (1 + MIN_EV) / p
    mo_w = _bisect(lambda x: stake_share(p, x) * BANKROLL, 1.0001, 1000.0, wager)
    print(f"   - Minimum odds for EV >= {MIN_EV:.0%}: {mo_ev:.2f}"
          + (f"   |   minimum odds that justify this wager: {mo_w:.2f}" if mo_w else
             "   |   no odds justify this wager (cap)"))
    if share > 0:
        print(f"   - Minimum bankroll for this wager to be allowed at these odds: {wager / share:.2f}")


def target_profit_check(odds, target, p, ev):
    """Stake needed to gain `target` if the bet wins, and what that stake means."""
    needed = max(target / (odds - 1.0), MIN_BET)
    allowed = stake_share(p, odds) * BANKROLL
    print(f"\n  Stake needed for a profit of {target:.2f} if it WINS:")
    print(f"   - Stake {needed:.2f} at odds {odds:.2f}  (profit {needed * (odds - 1):.2f} if it wins, "
          f"loss {needed:.2f} if it loses)")
    print(f"   - That is {needed / BANKROLL:.0%} of your bankroll; chance of losing it "
          f"{1 - p:.0%}; expected result of this wager {needed * ev:+.2f}")
    if allowed <= 0:
        print("   - Your Kelly settings say NO BET here, so this stake has no mathematical support: "
              "it is\n     a negative-expectation bet" + (" (expected loss shown above)." if ev < 0 else "."))
    elif needed > allowed * 1.0001:
        print(f"   - Your settings allow only {allowed:.2f}: this stake is {needed / allowed:.1f}x too "
              f"large. A profit of {target:.2f} is not\n     reachable safely at this price.")
    else:
        print(f"   - Within your Kelly settings (allowed {allowed:.2f}).")


def run(bet):
    odds = bet["market_odds"][bet["index"]]
    kw = dict(devig_method=DEVIG_METHOD, w_model=W_MODEL, se=SE, min_ev=MIN_EV,
              min_stake=MIN_BET, commission=COMMISSION)
    kw.update({"profile": PROFILE} if PROFILE else
              {"base_fraction": BASE_FRACTION, "max_stake_pct": MAX_STAKE_PCT})
    r = recommend_stake(bet["p_model"], odds, BANKROLL, bet["market_odds"], bet["index"], **kw)
    if LOG_RECOMMENDATIONS:
        log_recommendation(MATCH, bet["name"], bet["p_model"], r.p_market_fair, r.p_used, odds,
                           bet["market_odds"], bet["index"], r.ev, r.decision, r.stake, LOG_FILE)
    if EXPORT_FOR_ACCUMULATORS:
        export_to_matches(MATCH, bet["name"], bet["p_model"], odds, bet["market_odds"],
                          bet["index"], MATCHES_CSV)

    print("\n" + "-" * 78 + f"\n{bet['name']}  @ {odds}\n" + "-" * 78)
    print(r.report())
    gap = bet["p_model"] - r.p_market_fair
    print(f"\n  How to read it:"
          f"\n   1. Model vs fair market: {gap * 100:+.1f} points "
          f"({'model more bullish' if gap > 0 else 'model less bullish'} than the market)."
          f"\n   2. p used {r.p_used:.1%} vs break-even {r.breakeven:.1%}: "
          f"{'p used is higher -> there is an edge' if r.p_used > r.breakeven else 'p used is LOWER -> price too short'}."
          f"\n   3. EV {r.ev:+.2%} vs required {MIN_EV:.0%}: "
          f"{'passes' if r.ev >= MIN_EV else 'fails'}.")
    if r.ev >= MIN_EV and r.decision == "PASS":
        print(f"   4. EV passes but the decision is PASS: the stake your Kelly settings allow is "
              f"below MIN_BET ({MIN_BET:.2f}). Do not round it up.")

    min_odds = math.ceil((1 + MIN_EV) / r.p_used * 100) / 100
    print(f"\n  Price ladder (p used {r.p_used:.1%} held fixed; fraction {FRACTION:.3g}, cap {CAP:.0%}):")
    print(f"  {'odds':>8s}{'EV':>9s}{'stake':>9s}   note")
    for price, note in [(odds, "your price"), (min_odds, "MINIMUM to accept"),
                        (round(min_odds + 0.05, 2), ""), (round(min_odds + 0.10, 2), ""),
                        (round(min_odds + 0.20, 2), "")]:
        ev, st = stake_at(r.p_used, price)
        flag = "" if st >= MIN_BET or st == 0 else " (below MIN_BET)"
        print(f"  {price:>8.2f}{ev:>+9.1%}{st:>9.2f}   {note}{flag}")

    requirements(odds, MIN_BET, r.p_used, title="Requirements for the MINIMUM bet")
    if TARGET_PROFIT is not None:
        target_profit_check(odds, TARGET_PROFIT, r.p_used, r.ev)

    print(f"\n  Sensitivity to how much you trust the model (W_MODEL):")
    flips = []
    for w in (0.2, 0.4, 0.6, 0.8, 1.0):
        rr = recommend_stake(bet["p_model"], odds, BANKROLL, bet["market_odds"], bet["index"],
                             devig_method=DEVIG_METHOD, w_model=w, se=SE, min_ev=MIN_EV,
                             min_stake=MIN_BET, commission=COMMISSION,
                             **({"profile": PROFILE} if PROFILE else
                                {"base_fraction": BASE_FRACTION, "max_stake_pct": MAX_STAKE_PCT}))
        print(f"   w={w:.1f}  p {rr.p_used:.1%}  EV {rr.ev:+.2%}  {rr.decision}  stake {rr.stake:.2f}")
        if rr.ev >= MIN_EV:
            flips.append(w)
    if not flips:
        print("   -> PASS at every w: the price is simply not good enough.")
    else:
        print(f"   -> EV is only >= {MIN_EV:.0%} when you trust the model at w >= {min(flips):.1f}. "
              "That means the edge exists\n      only if the model is right and the market is wrong. "
              "Treat it as PASS until your own\n      logged bets show the model is calibrated.")
    return r, min_odds


def same_game():
    print("\n" + "=" * 78 + "\nSAME-GAME: home win AND Over 2.5\n" + "=" * 78)
    lam, mu = fit_lambdas(MODEL_1X2["home"], MODEL_OVER25)
    grid = score_grid(lam, mu, rho=-0.05)
    joint = grid_prob(grid, lambda i, j: i > j and i + j > 2.5)
    print(f"Fitted expected goals: home {lam:.2f}, away {mu:.2f}")
    print(f"Joint probability {joint:.1%} (naive product would be "
          f"{MODEL_1X2['home'] * MODEL_OVER25:.1%} - the legs are positively correlated)")
    ra = recommend_accumulator(
        [Leg("Home win", MODEL_1X2["home"], ODDS_1X2[0], ODDS_1X2, 0),
         Leg("Over 2.5", MODEL_OVER25, ODDS_OU25[0], ODDS_OU25, 0)],
        BANKROLL, combined_odds=SAME_GAME_ODDS, joint_model_p=joint, profile="conservative")
    print(ra.report())
    return ra


# =============================================================================
# 5. MAIN
# =============================================================================

def main():
    errors, warns = validate()
    print(f"MATCH: {MATCH}\nBANKROLL {BANKROLL:.2f}   MIN_BET {MIN_BET:.2f}   "
          f"PROFILE {PROFILE or 'custom'} (fraction {FRACTION:.3g}, cap {CAP:.0%})")
    for w in warns:
        print("WARNING:", w)
    if errors:
        for e in errors:
            print("ERROR:  ", e)
        sys.exit("Fix the errors above and run again.")

    print("\nMARGIN CHECK (bookmaker's built-in profit):")
    for label, odds in [("1X2", ODDS_1X2), ("Over/Under 2.5", ODDS_OU25)]:
        fair = DEVIG[DEVIG_METHOD](odds)
        print(f"  {label:15s} margin {overround(odds):.2%}   fair probabilities "
              f"{[f'{x:.1%}' for x in fair]}")

    results = [(b["name"],) + run(b) for b in BETS]
    if SAME_GAME_ODDS:
        ra = same_game()
        results.append(("Same-game combo", ra, None))

    if REQ_ODDS is not None and REQ_WAGER is not None:
        print("\n" + "=" * 78 + "\nREQUIREMENTS CHECK (your own odds + wager)\n" + "=" * 78)
        requirements(REQ_ODDS, REQ_WAGER, REQ_P)

    print("\n" + "=" * 78 + "\nVERDICT\n" + "=" * 78)
    for name, r, min_odds in results:
        if r.decision == "BET":
            print(f"  BET   {name}: stake {r.stake:.2f} ({r.stake_pct:.2%} of bankroll)")
        else:
            extra = f"  (take it only at odds >= {min_odds:.2f})" if min_odds else ""
            print(f"  PASS  {name}: EV {r.ev:+.2%}{extra}")

    print("""
BEFORE YOU PLACE ANY BET
  [ ] Odds re-checked on the bookmaker's site right now, same market, 90 minutes only
  [ ] Official line-ups checked (about 60 min before kick-off); no key absentee
  [ ] Bankroll updated, stake not rounded UP to the minimum bet
  [ ] Bet logged: model p, odds taken, stake, closing odds later, result
Keep the log for 200+ bets before you change W_MODEL or the Kelly fraction.
Next steps:  python betlog.py settle  |  python betlog.py report
             python check_accumulator.py   (combine singles from different matches)""")


if __name__ == "__main__":
    main()