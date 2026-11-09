"""Live NFL games from ESPN's public (unofficial) API -> our model's inputs."""
import re

import requests

SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={}"


def get_json(url):
    return requests.get(url, timeout=10).json()


def list_games():
    """Today's games: id, label, state ('pre' / 'in' / 'post')."""
    games = []
    for ev in get_json(SCOREBOARD).get("events", []):
        st = ev["status"]["type"]
        games.append({"id": ev["id"], "label": f'{ev["shortName"]}  ({st["shortDetail"]})',
                      "state": st["state"]})
    return games


def secs_left(period, clock):
    """Q1-Q4: 15-min quarters left + clock. Overtime: just the clock."""
    if period <= 4:
        return int((4 - period) * 900 + clock)
    return int(clock)


def yards_to_score(possession_text, offense_abbr):
    """'TB 40' with TB on offense -> 60 to go. 'CHI 40' with TB on offense -> 40. '50' -> 50."""
    m = re.match(r"([A-Z]+)?\s*(\d+)", (possession_text or "").strip())
    if not m:
        return None
    side, n = m.group(1), int(m.group(2))
    if side is None or n == 50:
        return 50
    return 100 - n if side == offense_abbr else n


def home_spread(details, home_abbr):
    """'CHI -6.5' -> +6.5 if CHI is home (our convention: + means home favored)."""
    if not details:
        return None
    if details.strip().upper() in ("EVEN", "PK", "PICK"):
        return 0.0
    m = re.match(r"([A-Z]+)\s*(-?\d+(?:\.\d+)?)", details.strip())
    if not m:
        return None
    fav, pts = m.group(1), abs(float(m.group(2)))
    return pts if fav == home_abbr else -pts


def game_state(event_id, last_possession=None):
    """Everything the model needs for one live game, plus ESPN's own number to compare."""
    ev = next((e for e in get_json(SCOREBOARD).get("events", []) if e["id"] == str(event_id)), None)
    if ev is None:
        return None
    comp = ev["competitions"][0]
    teams = {c["homeAway"]: c for c in comp["competitors"]}
    home, away = teams["home"], teams["away"]
    home_id, away_id = home["team"]["id"], away["team"]["id"]
    abbr = {home_id: home["team"]["abbreviation"], away_id: away["team"]["abbreviation"]}

    status = ev["status"]
    out = {
        "home": abbr[home_id], "away": abbr[away_id],
        "home_score": int(home.get("score") or 0), "away_score": int(away.get("score") or 0),
        "state": status["type"]["state"], "detail": status["type"]["shortDetail"],
        "secs_left": secs_left(status.get("period", 1), status.get("clock", 0.0)),
    }

    sit = comp.get("situation") or {}
    out["possession_text"] = sit.get("possessionText")
    out["down_distance"] = sit.get("downDistanceText")
    last = sit.get("lastPlay") or {}
    out["last_play"] = last.get("text")
    out["espn_home_wp"] = (last.get("probability") or {}).get("homeWinPercentage")

    # spread + current drive come from the game summary
    try:
        summ = get_json(SUMMARY.format(event_id))
    except Exception:
        summ = {}
    pick = summ.get("pickcenter") or []
    out["spread"] = home_spread(pick[0].get("details"), abbr[home_id]) if pick else None

    # who has the ball: situation -> current drive -> last known
    poss, source = sit.get("possession"), "situation"
    if not poss:
        drive_team = (((summ.get("drives") or {}).get("current") or {}).get("team") or {})
        poss, source = drive_team.get("id"), "current drive"
    if not poss:
        poss, source = last_possession, "last known"
    out["possession_id"], out["possession_source"] = poss, source
    out["home_has_ball"] = None if poss is None else str(poss) == str(home_id)

    offense = abbr.get(str(poss)) if poss else None
    out["yardline_100"] = yards_to_score(out["possession_text"], offense) if offense else None
    return out
