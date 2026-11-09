"""NFL win-probability dashboard: replay any game, see the swing plays, try your own situation."""
import altair as alt
import pandas as pd
import streamlit as st

from app.main import list_games, replay
from app.model import win_probability
from app import live

st.set_page_config(page_title="NFL Win Probability", page_icon="🏈", layout="wide")
st.title("🏈 NFL Win-Probability Engine")
st.caption("Logistic regression built from scratch on 300K+ NFL plays (2015–2022), "
           "tested on 2023–2025. Compared against nflverse's own model.")

tab_live, tab_replay, tab_whatif, tab_model = st.tabs(["🔴 Live", "Replay a game", "What-if", "How good is it?"])

# ---------------- Live ----------------
with tab_live:
    try:
        today = live.list_games()
    except Exception as e:
        today = []
        st.error(f"Could not reach ESPN: {e}")
    in_play = [g for g in today if g["state"] == "in"]
    if not today:
        st.info("No NFL games found today.")
    else:
        names = {g["id"]: ("🔴 " if g["state"] == "in" else "") + g["label"] for g in today}
        ids = [g["id"] for g in today]
        pick = st.selectbox("Today's games", ids, format_func=lambda i: names[i],
                            index=ids.index(in_play[0]["id"]) if in_play else 0)

        @st.fragment(run_every="20s")          # re-runs only this block every 20 s
        def live_panel(game_id):
            key = f"live_{game_id}"
            hist = st.session_state.setdefault(key, [])
            last_poss = st.session_state.get(key + "_poss")
            try:
                s = live.game_state(game_id, last_poss)
            except Exception as e:
                st.warning(f"ESPN fetch failed, retrying in 20 s ({e})")
                return
            if s is None:
                st.info("Game not found on today's scoreboard.")
                return
            st.session_state[key + "_poss"] = s["possession_id"]

            st.subheader(f'{s["away"]} {s["away_score"]} – {s["home_score"]} {s["home"]}   ·   {s["detail"]}')
            if s["state"] == "pre":
                st.info("Game hasn't started yet.")
                return
            spread = s["spread"] if s["spread"] is not None else 0.0
            if s["state"] == "post":
                p = 1.0 if s["home_score"] > s["away_score"] else 0.0 if s["home_score"] < s["away_score"] else 0.5
            elif s["home_has_ball"] is None or s["yardline_100"] is None:
                st.info("Waiting for ball position from ESPN…")
                return
            else:
                home_yards = s["yardline_100"] if s["home_has_ball"] else 100 - s["yardline_100"]
                p = win_probability(s["home_score"] - s["away_score"], s["secs_left"],
                                    s["home_has_ball"], home_yards, spread)

            if not hist or hist[-1]["detail"] != s["detail"] or hist[-1]["My model"] != round(p, 4):
                hist.append({"n": len(hist) + 1, "detail": s["detail"], "My model": round(p, 4),
                             "ESPN": s["espn_home_wp"], "play": s["last_play"] or ""})

            c1, c2, c3 = st.columns(3)
            c1.metric(f'{s["home"]} win prob (my model)', f"{p:.1%}")
            c2.metric(f'{s["home"]} win prob (ESPN)', "—" if s["espn_home_wp"] is None else f'{s["espn_home_wp"]:.1%}')
            c3.metric("Pre-game spread", f'{s["home"]} {spread:+g}' if s["spread"] is not None else "n/a (using 0)")
            st.caption(f'{s["down_distance"] or ""} · ball: {"home" if s["home_has_ball"] else "away"} '
                       f'(from {s["possession_source"]}) · last play: {(s["last_play"] or "")[:120]}')

            if len(hist) > 1:
                h = pd.DataFrame(hist).melt(id_vars=["n", "detail", "play"], value_vars=["My model", "ESPN"],
                                            var_name="model", value_name="p").dropna()
                ch = alt.Chart(h).mark_line(strokeWidth=2, point=True).encode(
                    x=alt.X("n:Q", title="update"),
                    y=alt.Y("p:Q", title=f'P({s["home"]} wins)', scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
                    color=alt.Color("model:N", scale=alt.Scale(domain=["My model", "ESPN"], range=["#2a78d6", "#eb6834"]),
                                    legend=alt.Legend(orient="top", title=None)),
                    tooltip=["model:N", alt.Tooltip("p:Q", format=".1%"), "detail:N", "play:N"])
                st.altair_chart(ch.properties(height=300), width="stretch")
            st.caption("Updates every 20 seconds while this page is open. The chart starts when you open the page.")

        live_panel(pick)


# ---------------- Replay ----------------
with tab_replay:
    games = pd.DataFrame(list_games())
    games["label"] = games.apply(
        lambda g: f"{g.season} wk {g.week}: {g.away_team} @ {g.home_team}", axis=1)
    games = games.sort_values(["season", "week"], ascending=[False, True])
    sb51 = "2016_21_NE_ATL"
    games.loc[games.game_id == sb51, "label"] = "⭐ Super Bowl LI: NE @ ATL (28–3 comeback)"
    options = [sb51] + [g for g in games.game_id if g != sb51]
    labels = dict(zip(games.game_id, games.label))

    game_id = st.selectbox("Pick a game", options, format_func=lambda g: labels[g])
    r = replay(game_id, top_swings=5)
    home, away = r["home_team"], r["away_team"]
    plays = pd.DataFrame(r["plays"])
    plays["play"] = range(1, len(plays) + 1)

    side = st.radio("Show win probability for", [home, away], horizontal=True,
                    index=1 if game_id == sb51 else 0)   # SB LI: show the Patriots' comeback
    flip = side == away
    plays["My model"] = 1 - plays["home_win_prob"] if flip else plays["home_win_prob"]
    plays["nflverse"] = (1 - plays["nflverse_home_wp"]) if flip else plays["nflverse_home_wp"]

    last = plays.iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("Final score", f"{away} {last.away_score} – {last.home_score} {home}")
    c2.metric(f"Lowest {side} win prob", f"{plays['My model'].min():.1%}")
    c3.metric(f"Highest {side} win prob", f"{plays['My model'].max():.1%}")

    long = plays.melt(id_vars=["play", "qtr", "time", "away_score", "home_score", "desc"],
                      value_vars=["My model", "nflverse"], var_name="model", value_name="p")
    chart = alt.Chart(long).mark_line(strokeWidth=2).encode(
        x=alt.X("play:Q", title="play number"),
        y=alt.Y("p:Q", title=f"P({side} wins)", scale=alt.Scale(domain=[0, 1]),
                axis=alt.Axis(format="%")),
        color=alt.Color("model:N", scale=alt.Scale(domain=["My model", "nflverse"],
                                                   range=["#2a78d6", "#eb6834"]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=[alt.Tooltip("model:N"), alt.Tooltip("p:Q", format=".1%", title="win prob"),
                 "qtr:Q", "time:N", "away_score:Q", "home_score:Q", "desc:N"],
    )
    half = alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(color="#999999", strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart((half + chart).properties(height=380).interactive(bind_y=False),
                    width="stretch")

    st.subheader("Top 5 swing plays")
    sw = pd.DataFrame(r["top_swings"])
    sw["swing"] = -sw["swing"] if flip else sw["swing"]
    sw["score"] = sw.apply(lambda s: f"{away} {s.away_score} – {s.home_score} {home}", axis=1)
    sw["swing"] = sw["swing"].map(lambda s: f"{s:+.0%}")
    st.dataframe(sw[["qtr", "time", "score", "swing", "desc"]], hide_index=True,
                 width="stretch")

# ---------------- What-if ----------------
with tab_whatif:
    st.write("Set up any game situation and see the home team's chance.")
    a, b = st.columns(2)
    lead = a.slider("Home lead (points)", -28, 28, 0)
    minutes = a.slider("Minutes left in the game", 0.0, 60.0, 30.0, step=0.5)
    has_ball = b.radio("Who has the ball?", ["Home", "Away"], horizontal=True) == "Home"
    yards = b.slider("Yards the offense needs to score", 1, 99, 75)
    spread = b.slider("Pre-game spread (+ = home favored)", -14.0, 14.0, 0.0, step=0.5)
    home_yards = yards if has_ball else 100 - yards
    p = win_probability(lead, minutes * 60, has_ball, home_yards, spread)
    st.metric("Home win probability", f"{p:.1%}")
    st.progress(p)

# ---------------- Model card ----------------
with tab_model:
    st.write("Test seasons 2023–2025, 130,811 plays. Lower log loss and Brier are better.")
    st.dataframe(pd.DataFrame({
        "model": ["Always guess the average", "nflverse home_wp (no spread)", "My logistic regression",
                  "My XGBoost (monotonic)", "nflverse vegas_home_wp"],
        "log loss": [0.6898, 0.4814, 0.4541, 0.4618, 0.4486],
        "Brier": [0.2483, 0.1627, 0.1503, 0.1523, 0.1486],
    }), hide_index=True, width="stretch")
    st.markdown(
        "- **Features:** home lead, time left, possession, field position, pre-game spread, "
        "and two interactions (lead × time elapsed, spread × time left).\n"
        "- **Calibration:** expected calibration error ≈ 0.01. When it says 70%, the home team wins about 70%.\n"
        "- **Why not XGBoost?** 300K plays but only ~1,800 independent games; trees overfit "
        "game-level noise. The simpler model generalized better.")
