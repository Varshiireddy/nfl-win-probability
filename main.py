"""FastAPI app: live win probability for any game state, plus replay of a past game."""
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.model import win_probability

app = FastAPI(title="NFL Win-Probability API")
DATA = Path(__file__).resolve().parent.parent / "data" / "replay.parquet"


class GameState(BaseModel):
    home_lead: int = Field(..., ge=-80, le=80, description="home score minus away score")
    secs_left: int = Field(..., ge=0, le=4500, description="game seconds remaining (3600 at kickoff)")
    home_has_ball: bool
    yardline_100: int = Field(..., ge=1, le=99, description="yards from the OFFENSE's goal line to score")
    spread: float = Field(0.0, ge=-30, le=30, description="pre-game spread, + means home favored")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/win-probability")
def predict(state: GameState):
    # convert to the home team's point of view, exactly like training
    home_yards = state.yardline_100 if state.home_has_ball else 100 - state.yardline_100
    p = win_probability(state.home_lead, state.secs_left, state.home_has_ball,
                        home_yards, state.spread)
    return {"home_win_prob": round(p, 4), "away_win_prob": round(1 - p, 4)}


@lru_cache
def load_plays():
    return pd.read_parquet(DATA)


@app.get("/games")
def list_games(season: int | None = None):
    plays = load_plays()
    if season is not None:
        plays = plays[plays["season"] == season]
    games = plays.drop_duplicates("game_id")[["game_id", "season", "week", "away_team", "home_team"]]
    return games.to_dict(orient="records")


@app.get("/replay/{game_id}")
def replay(game_id: str, top_swings: int = 5):
    plays = load_plays()
    g = plays[plays["game_id"] == game_id]
    if g.empty:
        raise HTTPException(status_code=404, detail=f"game {game_id} not found")

    rows = []
    for r in g.itertuples():
        has_ball = r.posteam == r.home_team
        home_yards = r.yardline_100 if has_ball else 100 - r.yardline_100
        lead = r.total_home_score - r.total_away_score
        p = win_probability(lead, r.game_seconds_remaining, has_ball, home_yards, r.spread_line)
        rows.append({"qtr": int(r.qtr), "time": r.time, "home_score": int(r.total_home_score),
                     "away_score": int(r.total_away_score), "home_win_prob": round(p, 4),
                     "nflverse_home_wp": None if pd.isna(r.vegas_home_wp) else round(float(r.vegas_home_wp), 4),
                     "desc": r.desc})

    # swing = how much this play moved the probability vs the previous play
    for i in range(len(rows)):
        prev = rows[i - 1]["home_win_prob"] if i > 0 else rows[0]["home_win_prob"]
        rows[i]["swing"] = round(rows[i]["home_win_prob"] - prev, 4)
    swings = sorted(rows, key=lambda r: abs(r["swing"]), reverse=True)[:top_swings]

    # the model doesn't know the game ended, so add a FINAL point: winner = 100%
    end = rows[-1]
    final_p = 1.0 if end["home_score"] > end["away_score"] else 0.0 if end["home_score"] < end["away_score"] else 0.5
    rows.append({**end, "time": "FINAL", "home_win_prob": final_p, "nflverse_home_wp": final_p,
                 "desc": "Game over", "swing": round(final_p - end["home_win_prob"], 4)})

    first = g.iloc[0]
    return {"game_id": game_id, "home_team": first.home_team, "away_team": first.away_team,
            "spread": float(first.spread_line), "n_plays": len(rows),
            "top_swings": swings, "plays": rows}
