from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def wp(**state):
    r = client.post("/win-probability", json=state)
    assert r.status_code == 200
    return r.json()["home_win_prob"]


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_probabilities_add_up():
    r = client.post("/win-probability",
                    json={"home_lead": 3, "secs_left": 1800, "home_has_ball": True, "yardline_100": 60}).json()
    assert abs(r["home_win_prob"] + r["away_win_prob"] - 1) < 1e-3


def test_late_lead_is_high():
    assert wp(home_lead=7, secs_left=120, home_has_ball=True, yardline_100=50) > 0.8


def test_bigger_lead_never_lowers_prob():
    probs = [wp(home_lead=l, secs_left=600, home_has_ball=False, yardline_100=60) for l in range(-21, 22)]
    assert all(b >= a for a, b in zip(probs, probs[1:]))


def test_favorite_beats_underdog_at_kickoff():
    fav = wp(home_lead=0, secs_left=3600, home_has_ball=False, yardline_100=75, spread=7)
    dog = wp(home_lead=0, secs_left=3600, home_has_ball=False, yardline_100=75, spread=-7)
    assert fav > 0.6 > 0.4 > dog


def test_bad_input_rejected():
    r = client.post("/win-probability",
                    json={"home_lead": 3, "secs_left": -5, "home_has_ball": True, "yardline_100": 60})
    assert r.status_code == 422


def test_replay_super_bowl_51():
    r = client.get("/replay/2016_21_NE_ATL").json()
    assert r["home_team"] == "ATL"
    lowest_for_ne = 1 - max(p["home_win_prob"] for p in r["plays"])
    assert lowest_for_ne < 0.05          # NE was nearly dead at 28-3...
    assert r["plays"][-1]["away_score"] > r["plays"][-1]["home_score"]   # ...and still won


def test_replay_unknown_game_404():
    assert client.get("/replay/1999_01_XXX_YYY").status_code == 404
