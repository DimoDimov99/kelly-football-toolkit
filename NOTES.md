Step Formula Function
Implied probability q = 1/d implied*prob
Bookmaker margin Σ(1/dᵢ) − 1 over all outcomes overround
Fair market probability pᵢ = (1/dᵢ) / Σ(1/dⱼ) (also power and Shin methods) devig*\*
Model probability P(i,j) = τ(i,j) · Pois(i; λ) · Pois(j; μ) score_grid, market_probs
Blend p = w·p_model + (1−w)·p_market, w ≈ 0.4 blend
Break-even 1/d recommend_stake
EV per 1 staked p·d − 1 expected_val
Kelly f* = (p·d − 1) / (d − 1) kelly_fraction
Exchange commission d_eff = 1 + (d−1)(1−c) effective_odds
Void bets (draw-no-bet) f* = (p_w·b − p_l) / (b·(p_w+p_l)) kelly_with_push
Uncertainty shrink edge² / (edge² + se²) recommend_stake

---

How to get “real” odds, step by step
Get the odds of every outcome in the market, not just your selection. For 1X2 that’s three prices, and for over/under it’s two.
Remove the margin with devig_shin (or devig_power) to get the market’s fair probability.
Get a model probability. Use ForzaPitch’s probability, or build your own from expected goals with score_grid and market_probs.
Blend the two. If you have no proof that your model beats the market, keep w at about 0.3–0.4.
Compare p with the break-even 1/d. If EV is below your minimum (default +2%), pass.
Size the stake with Kelly, a fraction (default quarter Kelly), the uncertainty shrink, and a cap of 3% of bankroll.

---

1. Why 1 - MODEL_OVER25?

Over 2.5 and Under 2.5 cover every possible result, since a match ends with 3 or more goals or with 2 or fewer. With a half-goal line there is no push, so the two probabilities add up to 100%. ForzaPitch shows only the Over number (73% for Viking), so Under is 1 − 0.73 = 0.27.

The "index": 1 picks the second price in ODDS_OU25, which is ordered [over, under]. So the Under bet uses the model’s Under probability with the bookmaker’s Under price. The 1X2 market is different: ForzaPitch gives home, draw and away separately, so you take them directly (away = index: 2, as you did). Your Bournemouth line is correct.

2. What EV is

EV (expected value) is the average profit per 1 staked if you could place the same bet many times at your probability:

EV = p × d − 1, or equivalently win chance × profit if it wins − lose chance × stake.

For your bet, p = 31.12% and the odds are 2.94:

It wins 31.12% of the time and pays +1.94: 0.3112 × 1.94 = +0.604
It loses 68.88% of the time and costs −1: −0.689
EV = 0.604 − 0.689 = −0.085, or −8.5%

On a stake of 20 you would expect to lose about 1.70 on average. A single bet either wins 1.94 per unit or loses 1, so EV is only the long-run average, not a prediction of one result. It is also only as good as the probability you put in.

3. Why the result is PASS, line by line

Margin 9.30%: the three outcomes’ implied probabilities add up to 109.3%. That is a high margin for a three-way market.
Raw implied 34.01%: 1/2.94. The bookmaker’s price assumes Bournemouth wins 34% of the time, but after the margin is removed the market’s own estimate is 30.97%.
Model p 31.35%: the model agrees with the market (+0.4 points). It sees no mispricing, so there is no edge to find.
p used 31.12%: the blend of the two, which is almost the same as either.
Break-even 34.01%: you need 34% to break even, but the true chance is about 31%. The gap is −2.9 points, and it is the bookmaker’s margin, not a model disagreement.
EV −8.51% is below your 2% minimum, so Kelly gives 0 and the stake is 0.00.
Sensitivity table: even with 100% trust in the model, EV is still −7.8%. The price is the problem, not how much you trust the model.

4. The price ladder

You’d need 3.28 or better for a 2% EV (fair odds are about 3.21).
Even at 3.48 (EV +8.3%) the stake is only 0.06, and at 3.80 about 0.23. All of these are below your MIN_BET of 0.50.
The reason is the uncertainty shrink: when an edge is small compared with your ±3 points of probability error, Kelly cuts the stake hard.
To reach a 0.50 stake with this probability you’d need odds around 4.4 or more, which isn’t a realistic price for this match.

5. What to do

At 2.94, this is a PASS. I wouldn’t treat the “EV +2.1% at 3.28” row as a bet: it would stake roughly zero.
Check other bookmakers or an exchange. The 9.3% margin on this 1X2 market is steep, and the same selection at another bookmaker might be 3.10 or higher.
Bankroll vs minimum bet: with 20 and a 0.50 minimum, even a clear edge produces stakes under the minimum. At 3.80, a bankroll of about 100 would give a 1.17 stake. A small bankroll means you can’t follow fractional Kelly properly, so don’t raise the stake to meet the minimum.
Fix the name if you like: "Bournemouth to win" (the spelling doesn’t affect the maths).
