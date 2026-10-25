"""
check_accumulator.py - pick 2-4 selections from matches.csv and get BET or PASS.

    python check_accumulator.py                       (shows numbered list, asks which to combine)
    python check_accumulator.py matches.csv 3,4,6     (rows 3, 4 and 6)
    python check_accumulator.py matches.csv 3,4,6 50  (same, with bankroll 50)

args: csv file | row numbers (1-based, comma separated) | bankroll (optional)

matches.csv is filled automatically by main.py (EXPORT_FOR_ACCUMULATORS = True), or edit it
by hand. Every selection must come from a DIFFERENT match.
The accumulator always uses the stricter accumulator settings (eighth Kelly, 1% cap,
3% minimum EV). The single-bet comparison uses PROFILE below.
"""
import sys

from betting_toolkit import recommend_accumulator, recommend_stake
from accumulator_scanner import load

# >>> keep these identical to BANKROLL / MIN_BET / PROFILE in main.py <<<
BANKROLL = 15.0      # your current betting bankroll
MIN_BET = 1.0        # smallest stake your bookmaker accepts
PROFILE = "standard"  # profile for the single-bet comparison


def main(path="matches.csv", picks=None, bankroll=BANKROLL):
    rows = load(path)
    if not rows:
        sys.exit("matches.csv is empty. Run main.py first (it exports its selections).")
    if picks is None:
        print("\nAvailable selections:")
        for i, (m, leg) in enumerate(rows, 1):
            print(f"  {i}. {leg.name:60s} odds {leg.odds}")
        picks = input("\nWhich to combine (e.g. 3,4,6)? ")
    try:
        idx = [int(x) for x in str(picks).replace(" ", "").split(",") if x]
        chosen = [rows[i - 1] for i in idx]
    except (ValueError, IndexError):
        sys.exit(f"Row numbers must be between 1 and {len(rows)}, e.g. 3,4,6.")
    if not 2 <= len(idx) <= 4:
        sys.exit("Choose 2 to 4 selections (more legs = more margin and error).")
    matches = [m for m, _ in chosen]
    if len(set(matches)) < len(matches):
        sys.exit("Two selections are from the same match: they are correlated and cannot be "
                 "multiplied.\nFor 'home win + Over 2.5' in one match use main.py "
                 "(SAME_GAME_ODDS).")
    legs = [leg for _, leg in chosen]

    print("\nEACH LEG AS A SINGLE BET")
    negative = []
    for leg in legs:
        r = recommend_stake(leg.p_model, leg.odds, bankroll, leg.market_odds, leg.market_index,
                            profile=PROFILE, min_stake=MIN_BET)
        print(f"  {leg.name:60s} EV {r.ev:+6.1%}  {r.decision:5s} stake {r.stake:.2f}")
        if r.ev < 0:
            negative.append(leg.name)

    ra = recommend_accumulator(legs, bankroll)
    too_small = ra.decision == "BET" and ra.stake < MIN_BET
    print("\nACCUMULATOR")
    print(ra.report())
    print("\n" + "=" * 60)
    if negative:
        print("VERDICT: PASS - the accumulator contains leg(s) with NEGATIVE value:\n  "
              + "\n  ".join(negative) + "\n  Remove them and re-check; they only lower your EV.")
    elif too_small:
        print(f"VERDICT: PASS - the accumulator has value, but the stake it supports "
              f"({ra.stake:.2f}) is below your minimum bet ({MIN_BET:.2f}).\n"
              f"  Do not round up. You would need a bankroll of about "
              f"{MIN_BET / max(ra.stake_pct, 1e-9):.0f} to bet it properly.")
    elif ra.decision == "BET":
        print(f"VERDICT: BET {ra.stake:.2f} on the {len(legs)}-leg accumulator "
              f"(combined odds {1 / ra.breakeven:.2f}, win chance {ra.p_used:.1%}).")
    else:
        print("VERDICT: PASS - this combination is not worth it at these prices.")
    print("=" * 60)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0] if a else "matches.csv", a[1] if len(a) > 1 else None,
         float(a[2]) if len(a) > 2 else BANKROLL)