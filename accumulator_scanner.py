"""
accumulator_scanner.py - check many matches at once and find the best accumulators.

    python accumulator_scanner.py                      (uses matches.csv, BANKROLL below)
    python accumulator_scanner.py matches.csv 50 4     (bankroll 50, up to 4 legs)

args: csv file | bankroll | max legs per accumulator (default 4)

CSV columns (main.py writes this file for you; one row per selection):
  match         name; legs from the SAME match are never combined (they are correlated).
                The names must be written identically for the same match.
  selection     text label
  p_model       model probability for this selection (0-1)
  odds          the price you can actually get on this selection
  market_odds   odds of ALL outcomes of that market, joined with |   e.g. 1.47|4.80|5.20
  market_index  position of your selection in market_odds (0 = first)
"""
import csv
import sys
from itertools import combinations

from betting_toolkit import Leg, recommend_accumulator, recommend_stake

# >>> keep these identical to BANKROLL / MIN_BET / PROFILE in main.py <<<
BANKROLL = 15.0
MIN_BET = 1.0
PROFILE = "standard"


def load(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            mo = [float(x) for x in r["market_odds"].split("|")] if r["market_odds"].strip() else None
            leg = Leg(f"{r['match']}: {r['selection']}", float(r["p_model"]), float(r["odds"]),
                      mo, int(r["market_index"] or 0))
            rows.append((r["match"], leg))
    return rows


def main(path="matches.csv", bankroll=BANKROLL, max_legs=4):
    rows = load(path)
    if not rows:
        sys.exit("matches.csv is empty. Run main.py first (it exports its selections).")

    print("\nSTEP 1 - every selection as a SINGLE bet")
    print(f"{'selection':60s}{'p_used':>8s}{'EV':>8s}{'decision':>10s}{'stake':>9s}")
    cands, singles_profit = [], 0.0
    for match, leg in rows:
        r = recommend_stake(leg.p_model, leg.odds, bankroll, leg.market_odds, leg.market_index,
                            profile=PROFILE, min_stake=MIN_BET)
        print(f"{leg.name:60s}{r.p_used:>8.1%}{r.ev:>+8.1%}{r.decision:>10s}{r.stake:>9.2f}")
        singles_profit += r.stake * r.ev
        if r.ev > 0:                       # only legs with a positive blended edge go in accas
            cands.append((r.ev, match, leg))
    cands.sort(key=lambda x: -x[0])
    cands = cands[:10]

    print(f"\nSTEP 2 - best accumulators from {len(cands)} positive-EV legs (max {max_legs} legs)")
    results = []
    for n in range(2, max_legs + 1):
        for combo in combinations(cands, n):
            if len({m for _, m, _ in combo}) < n:          # skip same-match combinations
                continue
            ra = recommend_accumulator([l for _, _, l in combo], bankroll)
            if ra.decision == "BET" and ra.stake < MIN_BET:
                ra.decision, ra.stake = "PASS", 0.0         # stake below the bookmaker minimum
                ra.notes.append(f"Stake below your minimum bet ({MIN_BET:.2f}).")
            results.append((ra.ev, ra, [l.name for _, _, l in combo]))
    results.sort(key=lambda x: (-(x[1].stake * x[0]), -x[0]))   # expected profit, then EV
    if not results:
        print("No valid combinations (need positive-EV legs from different matches).")
    for ev, ra, names in results[:5]:
        print(f"\n{ra.decision}  EV {ev:+.1%}  p {ra.p_used:.1%}  stake {ra.stake:.2f} "
              f"({ra.stake_pct:.2%})  expected profit {ra.stake * ev:+.3f}")
        print("   " + "\n   + ".join(names))
        for n in ra.notes:
            if n.startswith(("Best single", "Accumulator EV", "Stake below")):
                print("   -", n)

    print(f"\nExpected profit if you bet all single BETs above : {singles_profit:+.3f}")
    if results:
        print(f"Expected profit of the best accumulator          : "
              f"{results[0][1].stake * results[0][0]:+.3f}")
    print("\nRule of thumb: bet singles when they show BET; an accumulator only makes sense when "
          "its own\nstake above is positive AND its expected profit beats the singles.")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0] if a else "matches.csv", float(a[1]) if len(a) > 1 else BANKROLL,
         int(a[2]) if len(a) > 2 else 4)