# 🏈 NFL Win-Probability Engine

Predicts the home team's chance of winning at any moment of an NFL game, updated play by play.

**Data:** nflverse play-by-play, 2015–2025 (~470K plays)

## Progress
| Day | What | Result |
|---|---|---|
| 1 | Linear regression from scratch (NumPy, gradient descent) predicting final score margin | Test RMSE **9.86 pts** vs 14.21 baseline; matches scikit-learn |

## Key finding (Day 1)
Error drops from 10.5 pts in Q1 to 3.8 pts in Q4: a lead means more as time runs out,
which a linear model can't capture yet (fixed on Day 3 with a lead × time feature).

## Notebooks
- [Day 1: Linear regression](notebooks/day1_linear_regression.ipynb)
