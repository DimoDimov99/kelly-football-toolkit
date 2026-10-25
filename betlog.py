"""
betlog.py - bet log: records every recommendation, settles results, and reports whether
your model/program really works (calibration, ROI, closing-line value).

    python betlog.py list       show the log
    python betlog.py settle     enter results (and closing odds) for pending rows
    python betlog.py report     calibration, ROI and CLV summary

main.py calls log_recommendation() and export_to_matches() automatically.
Needs betting_toolkit.py in the same folder.
"""
import csv
import datetime
import os
import sys

from betting_toolkit import (bets_needed, brier, calibration_table, clv, log_loss,
                             roi_significance)

LOG_FILE = "bets_log.csv"
FIELDS = ["id", "timestamp", "match", "selection", "p_model", "p_market", "p_used", "odds",
          "market_odds", "market_index", "ev", "decision", "rec_stake", "actual_stake",
          "result", "closing_odds"]
MATCH_FIELDS = ["match", "selection", "p_model", "odds", "market_odds", "market_index"]


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _write(rows, path, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def _pipe(odds):
    return "|".join(str(o) for o in odds)


def log_recommendation(match, selection, p_model, p_market, p_used, odds, market_odds,
                       market_index, ev, decision, rec_stake, path=LOG_FILE):
    """Add (or refresh, if still unsettled) one row. Passes are logged too: they tell you
    whether the program's PASS decisions were right."""
    rows = [r for r in _read(path)
            if not ((r["match"], r["selection"]) == (match, selection) and not r["result"])]
    nid = max([int(r["id"]) for r in rows], default=0) + 1
    rows.append({"id": nid, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                 "match": match, "selection": selection, "p_model": round(p_model, 4),
                 "p_market": "" if p_market is None else round(p_market, 4),
                 "p_used": round(p_used, 4), "odds": odds, "market_odds": _pipe(market_odds),
                 "market_index": market_index, "ev": round(ev, 4), "decision": decision,
                 "rec_stake": rec_stake, "actual_stake": "", "result": "", "closing_odds": ""})
    _write(rows, path, FIELDS)


def export_to_matches(match, selection, p_model, odds, market_odds, market_index,
                      path="matches.csv"):
    """Append the selection to matches.csv so accumulator_scanner.py / check_accumulator.py
    can combine singles from different matches."""
    rows = [r for r in _read(path) if (r["match"], r["selection"]) != (match, selection)]
    rows.append({"match": match, "selection": selection, "p_model": p_model, "odds": odds,
                 "market_odds": _pipe(market_odds), "market_index": market_index})
    _write(rows, path, MATCH_FIELDS)


def list_log(path=LOG_FILE):
    rows = _read(path)
    if not rows:
        print("Log is empty.")
    for r in rows:
        print(f"#{r['id']:>3} {r['match'][:28]:28s} {r['selection'][:18]:18s} @{r['odds']:>5s} "
              f"{r['decision']:4s} rec {r['rec_stake']:>6s} placed {r['actual_stake'] or '-':>6s} "
              f"{r['result'] or 'pending'}")


def settle(path=LOG_FILE):
    rows = _read(path)
    pending = [r for r in rows if not r["result"]]
    if not pending:
        print("Nothing pending.")
        return
    try:
        for r in pending:
            print(f"\n#{r['id']} {r['match']} - {r['selection']} @ {r['odds']} "
                  f"(decision {r['decision']}, recommended stake {r['rec_stake']})")
            res = {"w": "won", "l": "lost", "v": "void"}.get(
                input("  Result [w=won, l=lost, v=void, Enter=skip]: ").strip().lower())
            if not res:
                continue
            r["result"] = res
            a = input(f"  Stake you ACTUALLY placed [Enter = {r['rec_stake']}, 0 = none]: ").strip()
            r["actual_stake"] = a if a else r["rec_stake"]
            r["closing_odds"] = input("  Closing odds of the whole market e.g. 3.0|3.8|2.0 "
                                      "[Enter = skip]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nStopped early - saving what you entered.")
    _write(rows, path, FIELDS)
    print("\nSaved.")


def report(path=LOG_FILE):
    rows = _read(path)
    settled = [r for r in rows if r["result"] in ("won", "lost")]
    print(f"Logged {len(rows)} | settled {len(settled)} | pending "
          f"{sum(1 for r in rows if not r['result'])}")
    if not settled:
        print("Settle some results first (python betlog.py settle).")
        return

    # 1. Honest probabilities? Compare model vs market vs blended on ALL settled rows.
    full = [r for r in settled if r["p_market"]]
    y = [1 if r["result"] == "won" else 0 for r in full]
    if full:
        print("\n1. PROBABILITY QUALITY (Brier score, lower = better)")
        scores = {}
        for name, key in [("model", "p_model"), ("market (fair)", "p_market"),
                          ("blended (used)", "p_used")]:
            p = [float(r[key]) for r in full]
            scores[name] = brier(p, y)
            print(f"   {name:15s} Brier {scores[name]:.4f}   log loss {log_loss(p, y):.4f}")
        best = min(scores, key=scores.get)
        print(f"   Best so far: {best}.", "The model is NOT beating the market: keep W_MODEL low."
              if best != "model" else "Model leads - but wait for 200+ results before trusting it.")
        print("   Model calibration (predicted vs actual hit rate):")
        for lo, hi, n, ap, ar in calibration_table([float(r["p_model"]) for r in full], y, 5):
            print(f"     {lo:.0%}-{hi:.0%}  n={n:<3d} predicted {ap:.0%}  actual {ar:.0%}")

    # 2. Money results of bets you really placed
    placed = [r for r in settled if float(r["actual_stake"] or 0) > 0]
    if placed:
        staked = sum(float(r["actual_stake"]) for r in placed)
        profit = sum(float(r["actual_stake"]) * (float(r["odds"]) - 1) if r["result"] == "won"
                     else -float(r["actual_stake"]) for r in placed)
        wins = sum(1 for r in placed if r["result"] == "won")
        print(f"\n2. BETS YOU PLACED: {len(placed)} bets, {wins} won, staked {staked:.2f}, "
              f"profit {profit:+.2f}, ROI {profit / staked:+.1%}")
        if len(placed) >= 2:
            sig = roi_significance([{"odds": float(r["odds"]), "won": r["result"] == "won"}
                                    for r in placed])
            print(f"   flat-stake ROI {sig['roi']:+.1%}, z-score {sig['z']:+.2f} "
                  f"(needs > 1.64 to suggest a real edge)")
            print(f"   To detect a true 2% edge you need about {bets_needed(0.02)} bets.")
    else:
        print("\n2. No placed bets recorded yet (enter your actual stake when settling).")

    # 3. Closing line value
    vals = []
    for r in rows:
        if r["closing_odds"] and float(r["actual_stake"] or r["rec_stake"] or 0) > 0:
            try:
                vals.append(clv(float(r["odds"]), [float(x) for x in r["closing_odds"].split("|")],
                                int(r["market_index"])))
            except Exception:
                pass
    if vals:
        print(f"\n3. CLOSING LINE VALUE: average {sum(vals) / len(vals):+.2%} over {len(vals)} bets "
              "(positive over 100+ bets = you beat the market's final price)")

    n = len(settled)
    print("\nVERDICT:", "too few results to conclude anything (aim for 200+)." if n < 50 else
          "enough for a first look, but treat conclusions as provisional until 200+." if n < 200
          else "sample is meaningful; compare Brier and CLV above.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    {"list": list_log, "settle": settle, "report": report}.get(cmd, report)()
