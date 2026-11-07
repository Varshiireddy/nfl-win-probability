"""Win-probability model: loads wp_model.json and turns a game state into P(home win)."""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MODEL = json.loads((ROOT / "models" / "wp_model.json").read_text())
MU = np.array(MODEL["mu"])
SD = np.array(MODEL["sd"])
W = np.array(MODEL["w"])
B = MODEL["b"]


def make_features(home_lead, secs_left, home_has_ball, home_yards_to_score, spread):
    """Exactly the same 7 features, in the same order, as in training."""
    frac_left = min(max(secs_left / 3600, 0.0), 1.0)
    x = {
        "home_lead": home_lead,
        "time_left": secs_left,
        "home_has_ball": float(home_has_ball),
        "home_yards_to_score": home_yards_to_score,
        "lead_x_time": home_lead * (1 - frac_left),
        "spread": spread,
        "spread_x_time": spread * frac_left,
    }
    return np.array([x[f] for f in MODEL["features"]], dtype=float)


def win_probability(home_lead, secs_left, home_has_ball, home_yards_to_score, spread):
    x = (make_features(home_lead, secs_left, home_has_ball, home_yards_to_score, spread) - MU) / SD
    z = x @ W + B
    return float(1 / (1 + np.exp(-z)))
