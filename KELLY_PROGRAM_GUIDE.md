# Kelly Betting Toolkit — Complete Guide

_Written 25 October 2026. Covers `betting_toolkit.py`, `main.py`, `betlog.py`, `check_accumulator.py`, `accumulator_scanner.py`, `matches.csv` and `bets_log.csv`._

> **Please read first.** This is an educational calculator. It cannot make a losing price profitable, it cannot predict football, and nothing here guarantees profit. Bookmakers build a margin into every price, and most bettors lose money over time. Only use money you can afford to lose completely, set limits in advance, and stop if betting stops being fun. If gambling is causing you stress or problems, talk to someone you trust or a local support service.

---

## Table of contents

1. What this program is (and is not)
2. The files and what each one does
3. Quick start in 10 minutes
4. The big ideas, explained like you are five
5. How the program decides, step by step
6. A complete worked example (real numbers from your Hoffenheim – Leverkusen run)
7. Every input in `main.py` (what, where to get it, how to verify it)
8. Every setting in `main.py` (what it does, how it is calculated, what to change)
9. How to read the report line by line
10. Warnings and errors: what they mean and what to do
11. Extra tools inside `main.py` (price ladder, sensitivity, minimum-bet check, target profit)
12. Accumulators (combining bets)
13. The bet log: tracking, settling and judging your results
14. Why fractional Kelly: the risk picture
15. Your routine for every match day
16. Free resources and prediction sources
17. Troubleshooting and frequently asked questions
18. Glossary
19. Parameter cheat sheet
20. Honest limits of this program

---

## 1. What this program is (and is not)

**What it is.** A set of small Python programs that answer three questions about a football bet:

1. **Is the price good?** Compare the bookmaker's price with a fair estimate of the real chance.
2. **If yes, how much should I stake?** Use the Kelly criterion, made safer with several protections.
3. **Is my method actually working?** Keep a log and measure it honestly over time.

**What it is not.**

- It is not a tipster. It does not know who will win. You supply a probability (for example from ForzaPitch), and the program checks whether the bookmaker's price pays enough for that probability.
- It is not a guarantee. A BET signal means "the numbers say the price may be worth it if the probability is right". It does not mean "this bet will win".
- It does not predict injuries, lineups or motivation. You must check those yourself.

**The most important truth.** In almost every match you check, the correct answer will be PASS. That is not a failure of the program. It is the program doing its job: protecting you from paying too much for a bet.

> **Kid version:** Imagine a shop that sells lottery-style tickets. The shop always charges a little more than the ticket is really worth. This program is a little helper that says, "Wait, this ticket costs more than it is worth. Don't buy it." Once in a while it says, "This one is a fair price or even cheap." Those are the rare times you might buy.

---

## 2. The files and what each one does

| File                     | What it is for                                                                            | Do you edit it?                          |
| ------------------------ | ----------------------------------------------------------------------------------------- | ---------------------------------------- |
| `betting_toolkit.py`     | The maths library. Everything else uses it.                                               | No.                                      |
| `main.py`                | Analyses one match. Your main program.                                                    | Yes: the inputs and settings at the top. |
| `betlog.py`              | Saves every recommendation, lets you enter results, and reports whether the method works. | No.                                      |
| `check_accumulator.py`   | Checks a chosen set of 2–4 selections as one accumulator.                                 | Only three constants at the top.         |
| `accumulator_scanner.py` | Scans all saved selections for the best accumulators.                                     | Only three constants at the top.         |
| `matches.csv`            | A table of selections. Filled in automatically by `main.py`.                              | Normally no.                             |
| `bets_log.csv`           | Your bet history. Filled in automatically.                                                | No (use `betlog.py`).                    |
| `example_viking.py`      | An old example. Replaced by `main.py`.                                                    | Delete it.                               |

**Requirements:** Python 3.8 or newer. Nothing else to install. Keep all the files in the same folder.

**Important consistency rule:** `BANKROLL`, `MIN_BET` and `PROFILE` appear at the top of `main.py`, `check_accumulator.py` and `accumulator_scanner.py`. Keep them identical in all three, otherwise the accumulator tools will use different numbers than your main analysis.

---

## 3. Quick start in 10 minutes

1. Put all the files in one folder.
2. Open the page for your match on ForzaPitch. Copy the three 1X2 percentages and the Over 2.5 percentage.
3. Open your bookmaker. Write down the decimal odds for **all** outcomes of the 1X2 market (home, draw, away) and both sides of the Over/Under 2.5 market. Use the same bookmaker and the same moment.
4. Open `main.py` and edit the inputs: `MATCH`, `BANKROLL`, `MIN_BET`, `MODEL_1X2`, `MODEL_OVER25`, `ODDS_1X2`, `ODDS_OU25`, and the `BETS` list.
5. Run `main.py` (command: `python main.py`).
6. Read the **VERDICT** section at the bottom. PASS means do not bet at this price. BET shows the stake.
7. Before betting, check the official lineups (about 60 minutes before kickoff) and re-check the odds.
8. After the match, run `python betlog.py settle` to record the result.

---

## 4. The big ideas, explained like you are five

### 4.1 Odds (the price)

**What it is.** Decimal odds tell you how much you get back for each 1 you stake, including your stake. Odds of 2.00 return 2 for every 1 staked (a profit of 1). Odds of 1.50 return 1.50 (a profit of 0.50).

**Kid version:** "If I give the shopkeeper one coin and my team wins, he gives me back two coins. That's odds of 2."

### 4.2 Implied probability (what the price says)

**What it is.** The chance the bookmaker's price is hinting at.

**Formula:** implied probability = 1 ÷ odds.

**Example:** odds of 1.93 → 1 ÷ 1.93 = 51.8%.

**Kid version:** "If the shopkeeper gives back two coins for one, he is saying he thinks I win about half the time."

### 4.3 The margin (the shop's profit)

**What it is.** Add up the implied probabilities of _all_ outcomes in a market. A fair market adds to exactly 100%. Real markets add to more, and the extra is the bookmaker's built-in profit.

**Formula:** margin = (sum of all 1 ÷ odds) − 1.

**Example (Hoffenheim – Leverkusen):** 1 ÷ 3.15 = 31.75%, 1 ÷ 3.75 = 26.67%, 1 ÷ 1.93 = 51.81%. The total is 110.23%, so the margin is **10.23%**. A typical football 1X2 margin is 4–7%, so this price is expensive.

**Kid version:** "The shopkeeper adds a little extra to every price, like a tax. The bigger the extra, the harder it is to win."

### 4.4 Fair probability (taking the tax away)

**What it is.** The market's real opinion after removing the margin. The program does this with a method called Shin (default). Two simpler methods are also available.

- **Multiplicative:** divide each implied probability by the total. Simple and fast.
- **Power:** raise each implied probability to a power chosen so the total is exactly 100%. It takes a bit more from the long-shot outcomes.
- **Shin:** assumes a small share of bettors have inside information, and solves for that share so the total is exactly 100%. Often used to correct the bias toward favourites and long shots.

**Example:** after removing the margin, the Hoffenheim – Leverkusen market says about 28.5% / 23.5% / 48.0% for home / draw / away.

**Kid version:** "If I take the shopkeeper's extra tax off, what price would he really have charged? That is the fair price."

### 4.5 Model probability (your helper's guess)

**What it is.** A probability from a model, for example ForzaPitch, which uses a Poisson goals model with a Dixon-Coles correction. The model estimates how many goals each team will score and turns that into chances for home/draw/away and over/under.

**Kid version:** "A friend who loves football numbers makes a guess about who will win. He is clever, but he does not know everything, like who is hurt today."

### 4.6 Blending (listening to both)

**What it is.** The program does not simply trust the model. It mixes the model with the market's fair probability.

**Formula:** probability used = (W_MODEL × model) + ((1 − W_MODEL) × market fair). With the default W_MODEL of 0.4, that is 40% model and 60% market.

**Why.** The betting market combines a huge amount of information (injuries, lineups, professional bettors). A simple public model usually knows less. If the model is wrong, blending protects you. If the model is right, you still capture part of its advantage.

**Kid version:** "My friend says Team A has a 35% chance. The whole town of shoppers says 48%. I listen to both, and I trust the town a little more."

### 4.7 Break-even probability

**What it is.** The chance you need for a bet to break even over many tries. It equals the implied probability (1 ÷ odds). If your best estimate of the true chance is lower than this, the bet loses money on average.

**Example:** at odds of 1.93 the break-even is 51.81%.

### 4.8 Expected value (EV)

**What it is.** The average profit per 1 staked if you could repeat the same bet many times.

**Formula:** EV = (probability used × odds) − 1.

**Example:** probability used 42.92%, odds 1.93 → 0.4292 × 1.93 − 1 = −0.1717, or **−17.17%**. On average you lose about 17 cents for every 1 you stake.

**Important:** EV does **not** depend on how much you stake. A 1 bet and a 10 bet at the same odds and probability have the same EV percentage. A single bet either wins or loses. EV only describes the long-run average.

**Kid version:** "If I played this game a thousand times, would I end up with more coins or fewer coins? EV says how many more or fewer, per coin."

### 4.9 Kelly criterion (how much to bet)

**What it is.** A formula that tells you the fraction of your money to stake to grow it fastest in the long run, if your probability is exactly right.

**Formula:** full Kelly = (probability × odds − 1) ÷ (odds − 1). If the result is zero or negative, do not bet.

**Example:** probability 56%, odds 2.00 → (0.56 × 2 − 1) ÷ (2 − 1) = 0.12, so 12% of your bankroll.

**The catch.** Full Kelly assumes you know the true probability. You never do. If your probability is a little too high, full Kelly over-bets and can ruin you. That is why this program uses several protections.

**Kid version:** "Kelly tells me how many coins to put in the game. A big edge means a few more coins. A tiny edge means almost none. No edge means keep my coins."

### 4.10 Fractional Kelly (being careful)

**What it is.** Betting only a share of full Kelly. Quarter Kelly (0.25) means a quarter of the full Kelly stake.

**Why.** It gives up a little growth in return for much smaller swings and protection against errors in your probability. See section 14 for the numbers.

**Kid version:** "The recipe says one cup of sugar. I'm not sure about the recipe, so I use a quarter cup first."

### 4.11 Uncertainty shrink

**What it is.** An extra safety factor in this program. When your edge is small compared with the error in your probability, the stake is cut sharply.

**Formula:** uncertainty factor = edge² ÷ (edge² + SE²), where edge = (probability used − break-even) and SE is your honest error on the probability (default 0.03 = 3 percentage points).

**Example:** an edge of 1.35 points with SE of 3 points gives 0.0135² ÷ (0.0135² + 0.03²) = about **0.17**. The stake is cut to a sixth. An edge of 4 points gives about 0.64.

**Kid version:** "If I'm only a tiny bit sure, I only put in a tiny bit."

### 4.12 Cap and minimum bet

- **Cap:** the largest stake as a share of your bankroll (default 3% for the standard profile). It stops any single bet from being too big.
- **Minimum bet (`MIN_BET`):** the smallest stake your bookmaker allows. If the stake the program calculates is below this, the answer is PASS. **Never round up to the minimum**, because that over-bets your edge.

---

## 5. How the program decides, step by step

For each selection, `main.py` runs these steps in order. Any step can stop the process with PASS.

1. **Validate your inputs** (typos, wrong totals, negative margins).
2. **Remove the margin** from the bookmaker's prices to get the market's fair probability.
3. **Blend** the model probability with the market's fair probability to get the probability used.
4. **Calculate EV** and compare with break-even. If EV is below `MIN_EV` (default 2%), the answer is PASS.
5. **Calculate full Kelly.**
6. **Multiply by the Kelly fraction** (for example 0.25).
7. **Multiply by the uncertainty factor.**
8. **Apply the cap** (for example 3% of bankroll).
9. **Convert to money** and round to two decimals.
10. **Check the minimum bet.** If the stake is below `MIN_BET`, the answer is PASS.

If every step passes, the verdict is BET with that stake.

---

## 6. A complete worked example (your Hoffenheim – Leverkusen run)

**Inputs.** Bankroll 15, minimum bet 1.00, standard profile. ForzaPitch: home 34.81%, draw 29.95%, away 35.24%, Over 2.5 60%. Bookmaker 1X2: 3.15 / 3.75 / 1.93. Over/Under 2.5: 1.28 / 3.30.

### Example A: Leverkusen to win at 1.93 (a clear PASS)

| Step                                     | Result               |
| ---------------------------------------- | -------------------- |
| Margin of the 1X2 market                 | 10.23%               |
| Market fair probability (Shin)           | 48.03%               |
| Model probability                        | 35.24%               |
| Probability used (40% model, 60% market) | 42.92%               |
| Break-even at 1.93                       | 51.81%               |
| Edge                                     | −8.90 points         |
| EV                                       | −17.17%              |
| Decision                                 | **PASS**             |
| Price the program would accept           | about 2.38 or higher |

**Plain explanation:** the bookmaker's price demands that Leverkusen win 51.8% of the time to break even. Even after trusting the market most, the best estimate is about 43%. You would lose about 17 cents per 1 on average.

### Example B: Under 2.5 goals at 3.30 (EV positive, but still PASS)

| Step                             | Result                                 |
| -------------------------------- | -------------------------------------- |
| Model probability                | 40.00%                                 |
| Market fair probability          | 26.09%                                 |
| Probability used                 | 31.65%                                 |
| Break-even                       | 30.30%                                 |
| EV                               | +4.46% (passes the 2% rule)            |
| Full Kelly                       | 1.94%                                  |
| Uncertainty factor               | 0.17                                   |
| After fraction (0.25) and shrink | 0.08% of bankroll                      |
| Stake on a 15 bankroll           | about 0.01                             |
| Minimum bet                      | 1.00                                   |
| Decision                         | **PASS (stake below the minimum bet)** |

**Plain explanation:** the numbers show a tiny edge, but it is so small compared with the error in the estimate that the correct stake is a cent. You cannot bet one cent, and you must not round up to 1.00.

**A second warning sign:** the model's goals forecast was low compared with what the page's own statistics showed (both teams' recent games had many goals), so the "value" is probably the model underestimating goals, not a real mistake by the bookmaker.

### Example C: A case where the answer is BET (illustrative, bankroll 1000)

Over 2.5 at 2.10 and Under 2.5 at 1.80, model says 60% for over.

| Step               | Result                                    |
| ------------------ | ----------------------------------------- |
| Probability used   | 51.62%                                    |
| Break-even         | 47.62%                                    |
| EV                 | +8.40%                                    |
| Full Kelly         | 7.64%                                     |
| Quarter Kelly      | 1.91%                                     |
| Uncertainty factor | 0.64                                      |
| Final              | 1.22% of bankroll, a stake of about 12.22 |
| Decision           | **BET**                                   |

Even here, the stake is only about 1.2% of the bankroll, not the 7.6% that full Kelly would suggest.

---

## 7. Every input in `main.py`

These are in section 1 of the file. Edit only these (and optionally the settings in section 2).

### MATCH

- **What:** a text label for the fixture, for example "Hoffenheim - Leverkusen - Bundesliga - 2026-10-25".
- **Where it matters:** it is saved to the log, and the accumulator tools use it to avoid combining two selections from the same match. Always use the exact same text for the same match.
- **Verify:** teams, date and kickoff must be the same fixture on the prediction page and on your bookmaker's coupon. Watch for date mismatches: the page's web address may contain a different date than the real kickoff.

### BANKROLL

- **What:** the money set aside only for betting that you can afford to lose completely.
- **How to set:** your current balance (after open bets). Update it before each session.
- **Kid version:** "The coins in my betting piggy bank, not my lunch money."

### MIN_BET

- **What:** the smallest stake your bookmaker accepts.
- **How to find:** look at the bet slip or the bookmaker's rules.
- **Why it matters:** with a small bankroll, the correct stake is often below the minimum, so the answer is PASS. If 3% of your bankroll is below the minimum, no bet can ever pass. With a bankroll of 15 and a minimum of 1.00, the cap is 0.45, so nothing can pass.

### MODEL_1X2

- **What:** the model's probabilities for home win, draw and away win.
- **Where from:** the "Pre-match analysis" block on the ForzaPitch match page.
- **How to enter:** as decimals: 34.81% becomes 0.3481.
- **Verify:** the three numbers must add up to about 1.00. The program stops with an error if they do not.
- **Sanity checks:** league table and recent form, the page's own statistics (goals scored and conceded, over/under rates), and team news that a model cannot know.

### MODEL_OVER25

- **What:** the model's probability of three or more goals.
- **How to enter:** 60% becomes 0.60. Under 2.5 is automatically 1 minus this.
- **Verify:** compare with the teams' recent over-2.5 rates and goals per game shown on the page. If the model's number is far below those, be suspicious of any "Under" value.

### ODDS_1X2

- **What:** the bookmaker's decimal odds for [home win, draw, away win], in that order.
- **How to enter:** all three numbers, same bookmaker, same moment.
- **Verify:** the market must be "Full time result / 90 minutes". Not draw-no-bet, not double chance. The margin reported by the program should usually be 3–8%. Prices move, so re-enter just before betting.

### ODDS_OU25

- **What:** the bookmaker's decimal odds for [over 2.5, under 2.5], in that order.
- **Verify:** the line must be exactly 2.5. Check that over is listed first.

### BETS

A list of the selections to evaluate. Each entry has four fields.

- **name:** a label, such as "Leverkusen win".
- **p_model:** the model probability for that selection (for example `MODEL_1X2["away"]`).
- **market_odds:** the odds list of that market (`ODDS_1X2` or `ODDS_OU25`).
- **index:** the position of the selection in that list, counting from 0. Home = 0, draw = 1, away = 2. Over = 0, under = 1.

The price you get is read from the odds list automatically (market_odds at the index), so the price and the market can never be entered inconsistently.

**Why Under 2.5 uses "1 minus over":** over and under cover every possible result of the match, and the 2.5 line has no tie, so the two probabilities add up to 100%. ForzaPitch only shows Over, so Under = 1 − Over.

### SAME_GAME_ODDS

- **What:** the bookmaker's price for a combined bet within one match (home win AND over 2.5). Leave as nothing (None) to skip.
- **Why separate:** the two parts are linked (when a team wins, more goals are usually scored), so their probabilities cannot be multiplied. The program builds a joint probability from a scoreline model and compares it with the bookmaker's own combined price.
- **Verify:** the price must be the bookmaker's "bet builder" or same-game price for exactly those selections.

### REQ_ODDS, REQ_WAGER, REQ_P (optional requirements check)

- **What:** an extra check for any odds and any wager: "what must be true for this wager to be worth it?"
- **REQ_ODDS:** the odds, or the total coefficient of an accumulator.
- **REQ_WAGER:** the stake you are considering.
- **REQ_P (optional):** your honest probability that it wins. For accumulators use the combined probability from the accumulator tool.
- **Leave all as None** to skip. (A requirements block at your minimum bet is always printed for each single bet.)

---

## 8. Every setting in `main.py`

These are in section 2 and further down section 1. The defaults are sensible. Change them only with evidence from your log.

### PROFILE

- **What:** a preset that sets both the Kelly fraction and the cap.
- **Options:**

| Profile      | Kelly fraction | Cap per bet (share of bankroll) |
| ------------ | -------------- | ------------------------------- |
| conservative | 0.10 (tenth)   | 1%                              |
| standard     | 0.25 (quarter) | 3%                              |
| aggressive   | 0.50 (half)    | 5%                              |

- **Set to None** to use `BASE_FRACTION` and `MAX_STAKE_PCT` instead.
- **Recommendation:** keep standard. Use conservative for your first 200 bets or for accumulators.

### BASE_FRACTION

- **What:** the Kelly fraction used when no profile is selected.
- **Allowed values:** "full" (1.0), "half" (0.5), "third" (0.333), "quarter" (0.25), "eighth" (0.125), "tenth" (0.1), or any number, or a fraction written like "1/4".
- **Kid version:** "How much of the recipe do I use? Full cup, half cup, or just a spoon?"

### MAX_STAKE_PCT

- **What:** the largest stake as a share of bankroll, used when no profile is selected. Default 0.03 (3%).
- **Why:** stops a single bet from hurting too much, even if the maths asks for more.

### W_MODEL (trust in the model)

- **What:** how much weight the model gets in the blend. 0.4 means 40% model, 60% market.
- **How it works:** probability used = W_MODEL × model + (1 − W_MODEL) × market fair.
- **Example:** model 35.24%, market 48.03%. At 0.4 the result is 42.92%. At 0.2 it is 45.47%. At 1.0 it is the model's 35.24%.
- **When to change:** raise to 0.5–0.6 only after 200 or more logged results show the model has a better (lower) Brier score than the market. Keep 0.3–0.4 if similar. Use 0.1–0.2 if the model is clearly worse.
- **Warning sign:** if a bet only passes when W_MODEL is high, the edge exists only if you believe the model over the market.

### SE (standard error of your probability)

- **What:** your honest estimate of how wrong your probability might be. 0.03 means plus or minus 3 percentage points.
- **How it works:** it enters the uncertainty factor. A larger SE shrinks stakes more.
- **When to change:** use 0.04–0.05 when the model and market disagree strongly, or in smaller leagues with less data.

### MIN_EV (minimum expected value)

- **What:** the smallest EV for which a bet is allowed. Default 0.02 (2%).
- **Why:** model errors of a few points can create fake small edges. A 2% filter removes most of that noise.

### DEVIG_METHOD

- **What:** how the bookmaker's margin is removed. "shin" (default), "power" or "multiplicative".
- **Effect:** small differences on favourites; larger differences on very long shots. Leave on "shin".

### COMMISSION

- **What:** commission charged on net winnings by a betting exchange, as a decimal (0.02 = 2%). Use 0 for a normal bookmaker.
- **How it works:** effective odds = 1 + (odds − 1) × (1 − commission).

### TARGET_PROFIT

- **What:** an information tool. "If I want to win this much when the bet wins, what stake is needed?"
- **Formula:** stake needed = target ÷ (odds − 1), but never below the minimum bet.
- **Example:** target 1.00 at odds 1.93 → 1.00 ÷ 0.93 = **1.08**. At odds 3.15 → 1.00 ÷ 2.15 = 0.47, raised to the 1.00 minimum bet.
- **What it also prints:** the share of your bankroll, the chance of losing that stake, the expected result, and whether your Kelly settings support that stake.
- **Honest warning:** for a PASS bet the expected result is negative at any stake. A bigger stake does not make a bad bet good. Never use this to try to win back losses.
- **Set to None** to hide.

### LOG_RECOMMENDATIONS, LOG_FILE

- **What:** save every BET and PASS to the bet log file (default `bets_log.csv`).
- **Why:** you cannot judge a method without records. Logging passes shows whether passing was right.

### EXPORT_FOR_ACCUMULATORS, MATCHES_CSV

- **What:** copy each selection to `matches.csv` so the accumulator tools can combine singles from different matches.

---

## 9. How to read the report line by line

| Line                      | Meaning                                                                |
| ------------------------- | ---------------------------------------------------------------------- |
| **Decision**              | BET or PASS. The answer.                                               |
| **Model p**               | The model's probability for the selection.                             |
| **Market fair p**         | The market's probability after removing the margin.                    |
| **raw implied**           | 1 ÷ odds, still including the margin.                                  |
| **p used (blended)**      | The mix of model and market. This is the probability the maths trusts. |
| **break-even**            | 1 ÷ odds. The chance needed to break even.                             |
| **EV per 1 staked**       | Average profit per 1 staked, using p used.                             |
| **prob. edge**            | p used minus break-even, in percentage points.                         |
| **Full Kelly**            | The theoretical stake if the probability were exact.                   |
| **Uncertainty factor**    | A 0–1 factor that shrinks the stake when the edge is small.            |
| **After fraction/shrink** | Full Kelly × Kelly fraction × uncertainty factor.                      |
| **FINAL STAKE**           | The money to stake after cap and minimum-bet checks.                   |
| **Notes**                 | Margin of the market, why a bet was passed, any cap applied.           |

**Reading order that works:** (1) Decision. (2) p used versus break-even: if p used is lower, the price is too short. (3) EV against your minimum. (4) Final stake.

**"How to read it" lines:** the program also prints a short plain-English version, including whether the model is more or less bullish than the market, whether p used beats break-even, whether EV passes, and (if relevant) that EV passes but the allowed stake is below the minimum bet.

---

## 10. Warnings and errors: what they mean and what to do

### Errors (the program stops)

| Message                                | Cause                                  | Fix                                      |
| -------------------------------------- | -------------------------------------- | ---------------------------------------- |
| Probabilities do not sum to about 100% | Typo or wrong numbers copied           | Re-copy from the page.                   |
| Probability must be between 0 and 1    | Entered 68.64 instead of 0.6864        | Use decimals.                            |
| Needs 3 (or 2) prices                  | Missing odds                           | Enter all outcomes of the market.        |
| Odds must be above 1.0                 | Wrong format (not decimal)             | Use decimal odds.                        |
| Margin is negative                     | Typo, or an arbitrage (extremely rare) | Re-check each price.                     |
| Index outside the list                 | Wrong position number                  | Home 0, draw 1, away 2; over 0, under 1. |
| REQ settings incomplete or invalid     | Only one of odds/wager set             | Set both, or neither.                    |
| TARGET_PROFIT must be positive         | Zero or negative value                 | Use a positive number or None.           |

### Warnings (the program continues)

| Warning                                        | Meaning                                                                                                                                   | What to do                                                                                                                        |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Margin below 1% or above 12%                   | Odds may be mistyped, or the wrong market                                                                                                 | Check each price.                                                                                                                 |
| Model and market differ by more than 12 points | Often a typo, a stale price, a different fixture or date, or news the model does not know. Often the model is simply missing information. | (1) Check inputs and fixture date. (2) Check odds are current. (3) Check team news. If all fine, trust the market, not the model. |
| Maximum stake below MIN_BET                    | Your bankroll is too small for your bookmaker's minimum, given the cap                                                                    | Lower minimum bet (if possible) or a larger bankroll. Do not raise the cap to fit.                                                |

---

## 11. Extra tools inside `main.py`

### Price ladder

Shows, holding the probability used fixed, what EV and stake you would get at higher odds. It includes your actual price, the **minimum price to accept**, and prices a little higher.

**Minimum price formula:** minimum odds = (1 + MIN_EV) ÷ probability used, rounded up to the next cent.

**Example:** probability used 42.92%, minimum EV 2% → 1.02 ÷ 0.4292 = 2.38.

**Use:** tells you what price would make the bet worth considering. Shop around for it.

### Sensitivity table (W_MODEL)

Re-runs the decision with the model weight at 0.2, 0.4, 0.6, 0.8 and 1.0. If the answer is PASS at every weight, the price is simply not good enough. If a bet only passes at high weights, you are relying on the model alone. Treat it as PASS until your own log proves the model.

### Requirements for the minimum bet

For a wager equal to your minimum bet, prints:

- Profit if it wins and loss if it loses.
- Break-even probability (1 ÷ odds).
- Probability needed for EV at least equal to your minimum (= (1 + MIN_EV) ÷ odds).
- The **probability that justifies this wager**: the lowest probability at which your Kelly settings would allow a stake that large. If your minimum bet is bigger than the cap, it can never be justified.
- With your probability: EV, expected profit on this wager, the stake your settings allow, whether you are over-betting, the minimum odds for EV and for the wager, and the **minimum bankroll** for the wager to be allowed (wager ÷ stake share).

### Target-profit stake

See TARGET_PROFIT in section 8.

### Important correction about "minimum bet for profit"

There is no stake size that makes a bet profitable on average. EV as a percentage is the same at any stake. What a stake changes is how much you win when it wins and how much you lose when it loses. The program's job is to say whether the price is worth betting at all and what stake fits your bankroll.

---

## 12. Accumulators (combining bets)

### 12.1 The key facts

- **Combined odds** = multiply the odds of all legs.
- **Combined probability** = multiply the probabilities used of all legs (only for different matches).
- **Margins compound.** Five legs with 5% margins each cost you about 28% in total built-in margin, not 5%.
- **Errors compound.** A small error in each leg's probability becomes a bigger error in the combined probability.
- **Accumulators win rarely.** A three-leg accumulator at combined odds of 3.3 may win only about one time in three, and larger ones far less often.

**Kid version:** "Betting one coin on one game is one chance to be right. An accumulator is like asking me to flip heads three times in a row. It pays more, but it is much harder."

### 12.2 Stricter defaults for accumulators

| Setting        | Singles        | Accumulators   |
| -------------- | -------------- | -------------- |
| Kelly fraction | quarter (0.25) | eighth (0.125) |
| Cap            | 3%             | 1%             |
| Minimum EV     | 2%             | 3%             |

### 12.3 How the combined uncertainty is calculated

Combined error ≈ combined probability × the square root of the sum of (SE ÷ each leg's probability) squared. This feeds the same uncertainty factor as for singles, which is why accumulator stakes become tiny.

### 12.4 Same-game combinations (for example home win AND over 2.5)

- Legs within one match are correlated. The program does not multiply them.
- It fits a scoreline model (Poisson with the Dixon-Coles correction) to the home-win and over-2.5 probabilities, then reads the joint probability from the scoreline table.
- The bookmaker's own combined price (SAME_GAME_ODDS) is converted to a market probability assuming a 10% margin, and blended with the model's joint probability.
- Because that 10% is an assumption, treat the result as indicative only.

### 12.5 Using `check_accumulator.py` (you pick the legs)

1. Run `main.py` for two or more different matches. Selections are saved to `matches.csv`.
2. Run `python check_accumulator.py`. It shows numbered selections and asks which to combine (2 to 4). Or give them directly, for example `python check_accumulator.py matches.csv 3,5,6`. An optional third argument sets the bankroll.
3. The program prints each leg's single-bet result, then the accumulator report, then the verdict.

**Verdict rules:**

- **PASS** if any leg has negative EV on its own (remove that leg and re-check).
- **PASS** if the stake the accumulator supports is below your minimum bet. It also tells you the bankroll you would need.
- **PASS** if the combined EV is below 3%.
- **BET** with a stake otherwise.
- Two selections from the same match are rejected.

### 12.6 Using `accumulator_scanner.py` (the program finds combinations)

1. Run `python accumulator_scanner.py` (optional arguments: file, bankroll, maximum legs, default 4).
2. Step 1 shows every selection as a single bet.
3. Step 2 takes up to the 10 best positive-EV selections, tries every combination of two to the maximum number of legs from different matches, and ranks them by expected profit in money, then by EV.
4. It ends by comparing the expected profit of the single bets with that of the best accumulator.

**Rule of thumb:** singles that show BET are usually better than combining them. An accumulator makes sense only if its own stake is positive and its expected profit beats the singles.

**Example (bankroll 1000):** two legs with combined odds of 3.33 gave EV of +7.8%, win chance about 32%, and a stake of only about 2.05 (0.21% of bankroll). With a bankroll of 15, the same legs support a stake of a few cents, below the minimum bet, so the verdict is PASS.

### 12.7 Limits

- Same-match detection depends on identical match names. Type them exactly the same.
- Different matches are treated as independent. Two matches in the same league on the same day are slightly linked, which is ignored.
- Bookmaker accumulator "boosts" change the odds. Enter the real combined price where the tool allows it.

---

## 13. The bet log: tracking, settling and judging your results

### 13.1 What gets saved

Every time `main.py` runs, each selection (BET or PASS) is saved to `bets_log.csv` with: time, match, selection, model probability, market fair probability, probability used, odds, all market odds, EV, decision and recommended stake. Re-running the same unsettled match and selection replaces the old row instead of duplicating it.

### 13.2 Commands

- **List:** `python betlog.py list` shows the log.
- **Settle:** `python betlog.py settle` goes through pending rows. For each, enter w (won), l (lost) or v (void), or press Enter to skip. Then enter the stake you actually placed (Enter accepts the recommended stake, 0 means you did not bet), and optionally the closing odds of the whole market, written like 3.0|3.8|2.0 with the vertical bar between them.
- **Report:** `python betlog.py report` prints the summary below.

### 13.3 What the report shows

1. **Probability quality (Brier score and log loss).** Compares the model, the fair market, and the blended probability on all settled rows. **Lower is better.** A guess of 50% on everything scores 0.25 on the Brier scale. If the market scores better than the model, the model is not adding information, and you should keep the model weight low. The calibration table shows, by probability band, what the model predicted against what actually happened. They should match.
2. **Bets you placed.** Number of bets, wins, amount staked, profit, ROI, and a z-score. **ROI** = profit ÷ amount staked. The **z-score** measures whether the profit is likely more than luck. A value above about 1.64 suggests (but does not prove) a real edge. The report also reminds you that detecting a true 2% edge takes about **6,700 bets**.
3. **Closing line value (CLV).** For bets where you entered closing odds, the average of (your odds × the closing fair probability − 1). A positive average over 100 or more bets means you tend to beat the market's final price, the best early sign of a real edge.

**Verdict by sample size:** fewer than 50 settled results is too few to conclude anything. 50–199 gives a provisional first look. 200 or more is meaningful.

**Kid version:** "I write down every guess and what really happened. After many games I can see if my guesses are really better than the town's guesses, or if I just got lucky."

### 13.4 Why logging passes matters

It shows whether the model's probabilities are honest, even for bets you did not place. Outcomes of passed selections still count in the Brier and calibration checks.

---

## 14. Why fractional Kelly: the risk picture

A simulation of 200 bets with a true win probability of 54% (the estimate was 56%, so 2 points too high), at odds of 2.00:

| Stake size    | Typical (median) result                | Chance of a 50% or worse drop at some point |
| ------------- | -------------------------------------- | ------------------------------------------- |
| Full Kelly    | about 1.61 times the starting bankroll | about 99%                                   |
| Half Kelly    | about 1.82 times                       | about 56%                                   |
| Quarter Kelly | about 1.48 times                       | about 5%                                    |

**What this teaches:** when your probability is a bit too optimistic (which is normal), full Kelly almost certainly suffers a huge drop at some point. Quarter Kelly gives up a little growth and removes most of the ruin risk. This is why the default is quarter Kelly with a cap.

Further risk facts: even with a real 2% edge, results over a few hundred bets are dominated by luck. A winning streak or a losing streak says little about skill.

---

## 15. Your routine for every match day

**Before the match**

1. Choose the match and open the model page. Confirm date, kickoff and teams.
2. Copy the probabilities (as decimals).
3. Copy the bookmaker's decimal odds for all outcomes. Same bookmaker, same time.
4. Edit `main.py` inputs and run it.
5. Read warnings first. Fix or understand every one.
6. Read the VERDICT. If PASS, you are done.
7. If BET: check official lineups (about 60 minutes before kickoff) and injuries, re-check the odds, re-run if anything changed.
8. Stake the printed amount, never more. Do not round up.

**Optional: accumulators**

9. After analysing at least two matches, run the accumulator checker or scanner. Prefer singles unless the accumulator clearly wins.

**After the match**

10. Run the settle command. Enter results, your actual stakes and closing odds.
11. Update `BANKROLL` in all three files.
12. Every few weeks, run the report. Do not change settings until you have 200 or more results.

**Checklist**

- Odds re-checked, same market, 90 minutes only
- Official lineups checked, no key absentee
- Bankroll updated, stake not rounded up
- Bet logged

---

## 16. Free resources and prediction sources

**Important:** no source gives a reliable winning edge. Sites that advertise high win rates, testimonials or "guaranteed" tips are marketing. A second independent probability is useful, and the betting market itself is usually the best estimate you have.

### Prediction models and probability sources

- **ForzaPitch** (forzapitch.com): free. Uses a Poisson regression with the Dixon-Coles correction, based on attacking and defending form, Elo rating, home advantage and league averages. Its page shows 1X2, over/under and score probabilities, plus recent form and tables. Treat its public track record (a small sample) with caution.
- **NeatSports Tipster** (neatsports.com/tipster): free. Describes a bivariate Poisson model with a Dixon-Coles correction and shows over/under, both-teams-to-score and 1X2.
- **Statlyzer**: a newer, smaller tool describing Poisson, Dixon-Coles and Monte Carlo methods. Check that it publishes results against predictions before trusting it.
- **FootySim** (stats.footysim.io): free. Elo-based Monte Carlo simulation with probabilities for many leagues, updated daily, drawing its club ratings from ClubElo. Independent of goal-based models, which makes it a good second opinion.
- **ClubElo** (clubelo.com): free club Elo ratings, with a free data interface.
- **Forebet** and **FootyStats**: free sites with over/under and 1X2 probabilities and statistics. Their exact methods are not fully documented, so use them only for comparison.

### Team news, lineups and injuries

- **Flashscore**, **Sofascore** and **FotMob**: predicted and official lineups, injuries and suspensions.
- **Transfermarkt** and **Squawka**: injury lists with expected return dates.
- **Club websites and press conferences**, and **official lineups about 60 minutes before kickoff**: the most reliable.

### Data for building and testing models

- **football-data.co.uk**: free historical results and closing odds from several bookmakers in downloadable files. Very useful for testing a model against the market.
- **Understat** and **FBref**: free expected-goals and match statistics (FBref's data is based on Opta).
- **StatsBomb Open Data**: free event data for study.
- **penaltyblog** (Python library): free, includes Dixon-Coles models if you want to build your own.
- **quantitative_sports** (Python package): free, but built for American football, not for football/soccer.

### Using more than one source

Average two independent probabilities (for example a goals model and an Elo model) and enter the average as the model probability. If they disagree by more than about 8 points, treat the bet as a PASS. Keep the market blend: it already contains most of what public models know.

---

## 17. Troubleshooting and frequently asked questions

**The program says PASS on everything. Is it broken?**
No. It is the normal result. Bookmaker margins of 7–10% leave very little room, and a public model rarely beats the market.

**Why is the stake 0.00 when EV is positive?**
Either the stake is below your minimum bet, or the uncertainty factor shrank a small edge to almost nothing. The report notes will say which.

**Why does the maximum stake warning appear?**
Your bankroll multiplied by the cap is below your minimum bet. Only a lower minimum or a larger bankroll fixes this.

**The model and the market disagree by 13 points. Do I have a big edge?**
Almost certainly not. The model is most likely missing information, or an input is wrong. Check the fixture date, odds, and team news, then trust the market.

**Should I raise W_MODEL to find more bets?**
No. Only raise it after 200 or more logged results show the model beats the market on the Brier score.

**Can I make my bet "profitable" with a bigger stake?**
No. A bigger stake only scales both the possible win and the possible loss. The EV percentage stays the same.

**Why not bet Kelly on every positive-EV bet?**
Your probabilities are estimates. Full Kelly with an overestimated probability loses money. That is why there is a fraction, a cap, an uncertainty shrink and a minimum EV.

**Can I combine singles into an accumulator?**
Yes, with `check_accumulator.py` or `accumulator_scanner.py`, using selections from different matches. Singles are usually better.

**What if the odds change?**
Re-enter them and re-run. The price ladder shows what price you would need.

**What does "void" mean when settling?**
The bet was cancelled and the stake returned (for example a postponed match). It counts as neither a win nor a loss.

**The accumulator tool shows a different stake from main.py.**
Check that `BANKROLL`, `MIN_BET` and `PROFILE` are identical in all three files.

**Why does the log have an empty market probability?**
Only when no market odds were supplied. Then the model probability is used unblended, which is risky.

**Who should I contact if gambling worries me?**
A trusted person or a local support organisation. If betting stops being entertainment, stop.

---

## 18. Glossary

- **Accumulator (parlay):** one bet made of several selections that must all win.
- **Bankroll:** money reserved only for betting.
- **Blend:** mixing the model probability with the market probability.
- **Break-even probability:** 1 ÷ odds; the win chance needed to break even.
- **Brier score:** an accuracy score for probability forecasts. Lower is better.
- **Calibration:** whether events predicted at 60% really happen about 60% of the time.
- **CLV (closing line value):** how your odds compare with the market's final price.
- **Decimal odds:** the total return per 1 staked, including the stake.
- **De-vig:** removing the bookmaker's margin from prices.
- **Dixon-Coles:** a correction to the Poisson model that adjusts the chances of low scores (0-0, 1-0, 0-1, 1-1).
- **Edge:** probability used minus break-even probability.
- **EV (expected value):** average profit per 1 staked.
- **Fair probability:** the market probability after the margin is removed.
- **Kelly criterion:** formula for the stake that maximises long-run growth.
- **Margin (overround, vig):** the bookmaker's built-in profit.
- **Poisson model:** a way to turn expected goals into the chances of each scoreline.
- **Push or void:** a bet where the stake is returned.
- **ROI:** profit divided by the total amount staked.
- **SE (standard error):** the likely size of error in a probability.
- **Shin method:** a way to remove the margin that accounts for insider money.
- **xG (expected goals):** the number of goals a team is expected to score.
- **z-score:** how many standard errors a result is from zero; used to judge whether profit is more than luck.

---

## 19. Parameter cheat sheet

| Parameter                  | Default  | Plain meaning                                           | Change when                               |
| -------------------------- | -------- | ------------------------------------------------------- | ----------------------------------------- |
| BANKROLL                   | yours    | Money set aside for betting                             | Every session                             |
| MIN_BET                    | yours    | Smallest stake the bookmaker accepts                    | If the bookmaker changes it               |
| PROFILE                    | standard | Preset of Kelly fraction and cap                        | Rarely; conservative for new models       |
| BASE_FRACTION              | quarter  | Share of full Kelly (only if no profile)                | Rarely                                    |
| MAX_STAKE_PCT              | 3%       | Largest stake as share of bankroll (only if no profile) | Rarely                                    |
| W_MODEL                    | 0.4      | How much to trust the model versus the market           | After 200+ logged results                 |
| SE                         | 0.03     | Honest error of your probability                        | Larger when the model and market disagree |
| MIN_EV                     | 2%       | Smallest EV worth betting                               | Rarely                                    |
| DEVIG_METHOD               | shin     | How the margin is removed                               | Rarely                                    |
| COMMISSION                 | 0        | Exchange commission                                     | Only on exchanges                         |
| TARGET_PROFIT              | 1.00     | Profit target for the stake-needed display              | Any time; None hides it                   |
| LOG_RECOMMENDATIONS        | True     | Save every recommendation                               | Keep on                                   |
| EXPORT_FOR_ACCUMULATORS    | True     | Save selections for accumulator tools                   | Keep on                                   |
| SAME_GAME_ODDS             | None     | Price of a same-game combination                        | When you want that check                  |
| REQ_ODDS, REQ_WAGER, REQ_P | None     | Custom requirements check                               | When you want it                          |

**Built-in constants (inside the toolkit, not normally changed):**

- Kelly fractions: full 1.0, half 0.5, third 0.333, quarter 0.25, eighth 0.125, tenth 0.1.
- Accumulator defaults: eighth Kelly, 1% cap, 3% minimum EV, leg error 3 points.
- Same-game assumed margin: 10%.
- Dixon-Coles correlation parameter for same-game: −0.05.

---

## 20. Honest limits of this program

1. **Garbage in, garbage out.** The program cannot tell whether your probability is true. A positive EV from a flawed input is not a real edge.
2. **No information about today.** Injuries, lineups, weather and motivation are not included.
3. **Prices move.** A BET at one moment can be a PASS ten minutes later.
4. **Small bankroll constraint.** With a small bankroll and a fixed minimum bet, the correct stake is often below the minimum. That is a real limit of the situation, not a bug.
5. **Variance is large.** Even with a real edge, a few hundred bets can look bad or good by luck alone. The log needs 200 or more results, and a true 2% edge needs thousands.
6. **Independence assumption.** Accumulator legs from different matches are treated as independent.
7. **Defaults are starting points.** The weights and thresholds are sensible but not proven optimal for your leagues.
8. **It is a filter, not a money machine.** Its best value is stopping you from making bad bets and keeping honest records.

---

Model sources:

- https://forzapitch.com/
- https://stats.footysim.io/
