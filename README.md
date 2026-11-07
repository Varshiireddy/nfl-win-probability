# 🏈 NFL Win-Probability Engine

Predicts the home team's chance of winning an NFL game, updated **play by play**, the same idea as the win-probability graphs ESPN and Google show during live games.

Built from scratch in NumPy first, then checked against scikit-learn, then extended with better models, an API and a live dashboard.

> **Status:** 🚧 In progress: Day 2 of 7

---

## The problem

Given the state of a game at any moment, **what is the probability that the home team wins?**

| Input (game state) | Output |
|---|---|
| Score lead, time left, who has the ball, field position | P(home team wins), e.g. **0.91** |

**Data:** free NFL play-by-play from [nflverse](https://github.com/nflverse), loaded with [`nflreadpy`](https://github.com/nflverse/nflreadpy). That's every play from the 2015–2025 seasons, about 500,000 plays.

**Train/test split by season:** train on 2015–2022, test on 2023–2025. The model never sees the future, just like in real life.

---

## Progress

### ✅ Day 1: Linear regression from scratch
**Notebook:** [`notebooks/day1_linreg.ipynb`](notebooks/day1_linreg.ipynb)

- Predicts the **final score margin** from the current game state
- Gradient descent written in NumPy, checked against scikit-learn
- Test seasons 2023–2025: **RMSE X.XX points** vs **X.XX** for always guessing the average

### ✅ Day 2: Logistic regression from scratch
**Notebook:** [`notebooks/day2_logreg.ipynb`](notebooks/day2_logreg.ipynb)

- Predicts **P(home team wins)** using a sigmoid and cross-entropy loss (maximum likelihood)
- Every feature rebuilt from the **home team's point of view** (raw nflverse columns are measured from the team with the ball)
- My NumPy weights match scikit-learn within **0.01**

| Model | Test log loss ↓ | Accuracy ↑ |
|---|---|---|
| Baseline (always guess the home win rate) | X.XXX | XX% |
| **Logistic regression (mine)** | **X.XXX** | **XX%** |

**Sanity checks**

| Situation | Model's home win chance |
|---|---|
| Up 7, 2 min left, home ball at midfield | XX% |
| Tied at kickoff | XX% |
| Down 7, 2 min left, away ball | XX% |

**What I learned:** the `time_left` weight is close to 0. Time on its own doesn't predict a winner; it only matters **combined with the lead** (a 7-point lead with 1 minute left is huge, with 59 minutes left it isn't). Day 3 fixes this with a lead × time feature.

| 3 | Feature engineering, leakage check, GroupKFold CV, L1/L2 | Log loss 0.496 → 0.454, acc 74.3% → 77.7%. Spread helped most; timeouts/down didn't (L1 zeroed them). Best λ = 0 |

| 4 | Calibration, Brier, ROC-AUC, comparison vs nflverse | ECE ≈ 0.01; Brier 0.150 (skill 0.40); AUC 0.864. Beats nflverse home_wp (0.481 log loss); within 0.006 of vegas_home_wp (0.449) |

---

## Roadmap

- [x] **Day 1:** Linear regression from scratch
- [x] **Day 2:** Logistic regression from scratch
- [ ] **Day 3:** Feature engineering (lead × time, timeouts, down and distance, pre-game spread), cross-validation, L1/L2 regularization
- [ ] **Day 4:** Calibration: when the model says 70%, does the team win 70% of the time? Compared with nflverse's built-in win probability
- [ ] **Day 5:** XGBoost with monotonic constraints, MLflow tracking, SHAP explanations
- [ ] **Day 6:** FastAPI `POST /win-probability` endpoint, Docker, pytest, GitHub Actions
- [ ] **Day 7:** Streamlit dashboard: replay any game (e.g. the Super Bowl LI comeback from 28–3) and highlight the biggest swing plays

---

## Run it yourself

The easiest way is to click **"Open in Colab"** at the top of any notebook. Or run it locally:

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
pip install -r requirements.txt
jupyter notebook notebooks/
```

The first run downloads about 11 seasons of play-by-play and caches it as `pbp_2015_2025.parquet` (not committed to the repo).

---

## Tech stack

Python · NumPy · pandas · scikit-learn · nflreadpy · Google Colab
*Coming this week:* XGBoost · SHAP · MLflow · FastAPI · Docker · pytest · GitHub Actions · Streamlit
