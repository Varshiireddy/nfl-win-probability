"""Build data/replay.parquet: plays for every 2023-2025 game + Super Bowl LI (2016)."""
import nflreadpy as nfl
import pandas as pd

COLS = ["game_id", "season", "week", "play_type", "home_team", "away_team", "qtr", "time", "desc",
        "posteam", "game_seconds_remaining", "yardline_100",
        "total_home_score", "total_away_score", "spread_line", "vegas_home_wp"]

parts = [nfl.load_pbp([s]).select(COLS).to_pandas() for s in [2023, 2024, 2025]]
sb51 = nfl.load_pbp([2016]).select(COLS).to_pandas()
parts.append(sb51[sb51["game_id"] == "2016_21_NE_ATL"])

plays = pd.concat(parts, ignore_index=True)
NEEDED = ["posteam", "spread_line", "yardline_100", "game_seconds_remaining",
          "total_home_score", "total_away_score", "qtr"]
plays = plays.dropna(subset=NEEDED)          # no blanks: the API cannot send NaN in JSON
# kickoffs / extra points: posteam is the KICKING team there, which fakes big swings
plays = plays[plays["play_type"].isin(["run", "pass", "punt", "field_goal", "qb_kneel", "qb_spike", "no_play"])]
plays.to_parquet("data/replay.parquet", index=False)
print(plays.shape, plays["game_id"].nunique(), "games")
