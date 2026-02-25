import streamlit as st
import pandas as pd
import random
import datetime
import os

# --- 1. DATA LOADING ---
@st.cache_data
def load_data():
    people = pd.read_csv('People.csv')
    appearances = pd.read_csv('Appearances.csv')
    allstar = pd.read_csv('AllstarFull.csv')
    teams = pd.read_csv('Teams.csv')
    batting = pd.read_csv('Batting.csv') if os.path.exists('Batting.csv') else None
    pitching = pd.read_csv('Pitching.csv') if os.path.exists('Pitching.csv') else None
    
    as_counts = allstar.groupby('playerID').size().to_dict()
    recent_teams = teams.sort_values('yearID', ascending=False).drop_duplicates('teamID').set_index('teamID')['name'].to_dict()
    max_year_limit = appearances['yearID'].max()
    last_seasons = appearances.groupby('playerID')['yearID'].max().to_dict()
    
    pos_cols = ['G_p', 'G_c', 'G_1b', 'G_2b', 'G_3b', 'G_ss', 'G_lf', 'G_cf', 'G_rf']
    player_primary = appearances.groupby('playerID')[pos_cols].sum().idxmax(axis=1).to_dict()
    
    people['fullName'] = people['nameFirst'].fillna('').astype(str) + " " + people['nameLast'].fillna('').astype(str)
    name_to_id = people.set_index('fullName')['playerID'].to_dict()
    id_to_name = people.set_index('playerID')['fullName'].to_dict()

    stats_dict = {}
    for pid in people['playerID'].unique():
        s = {"type": "Position"}
        if player_primary.get(pid) == 'G_p':
            s["type"] = "Pitcher"
            if pitching is not None:
                p_stats = pitching[pitching['playerID'] == pid].sum(numeric_only=True)
                s.update({"W": int(p_stats.get('W', 0)), "SO": int(p_stats.get('SO', 0))})
        else:
            if batting is not None:
                b_stats = batting[batting['playerID'] == pid].sum(numeric_only=True)
                s.update({"HR": int(b_stats.get('HR', 0)), "H": int(b_stats.get('H', 0)), "SB": int(b_stats.get('SB', 0))})
        stats_dict[pid] = s
    return people, appearances, as_counts, recent_teams, player_primary, name_to_id, id_to_name, stats_dict, last_seasons, max_year_limit

p_df, app_df, as_counts, recent_teams, player_primary, name_to_id, id_to_name, stats_dict, last_seasons, max_yr = load_data()

# --- 2. LOGIC ---
def generate_chain():
    today = datetime.date.today()
    day_idx = today.weekday()
    random.seed(int(today.strftime("%Y%m%d")))
    
    diff_settings = {
        0: {"threshold": 5, "lbl": "MON: HALL OF FAME (5+ ASG)", "clr": "#00FF41"},
        1: {"threshold": 4, "lbl": "TUE: LEGENDS (4+ ASG)", "clr": "#00D4FF"},
        2: {"threshold": 3, "lbl": "WED: ALL-STARS (3+ ASG)", "clr": "#FFD700"},
        3: {"threshold": 2, "lbl": "THU: VETERANS (2+ ASG)", "clr": "#FF8C00"},
        4: {"threshold": 1, "lbl": "FRI: DEEP CUTS (1+ ASG)", "clr": "#FF4B4B"},
    }
    d = diff_settings.get(day_idx, diff_settings[4])
    
    pos_list = ['G_p', 'G_c', 'G_1b', 'G_2b', 'G_3b', 'G_ss', 'G_lf', 'G_cf', 'G_rf']
    lbl_list = ["Pitcher", "Catcher", "1st Base", "2nd Base", "3rd Base", "Shortstop", "Left Field", "Center Field", "Right Field"]
    
    starters = ['maddugr01', 'ryanno01', 'johnsra01', 'kershcl01'] if d["threshold"] >= 4 else ['salech01', 'degroja01', 'scherma01']
    curr_pid = random.choice(starters)
    next_conn = {"year": None, "team": None}
    chain = []

    for i in range(9):
        bio = p_df[p_df['playerID'] == curr_pid].iloc[0]
        st_data = stats_dict.get(curr_pid, {})
        end_yr = "Active" if last_seasons.get(curr_pid) == max_yr else str(last_seasons.get(curr_pid))
        
        rep = f"📊 {str(bio['debut'])[:4]}—{end_yr}  |  🌟 {as_counts.get(curr_pid,0)}x All-Star\n"
        if st_data.get("type")=="Pitcher":
            rep += f"Wins: {st_data.get('W',0)}  |  K: {st_data.get('SO',0)}"
        else:
            rep += f"Hits: {st_data.get('H',0)}  |  HR: {st_data.get('HR',0)}  |  SB: {st_data.get('SB',0)}"

        chain.append({
            "pos": lbl_list[i], "name": id_to_name.get(curr_pid), "pid": curr_pid, "report": rep,
            "year": next_conn["year"], "team": next_conn["team"], "diff": d,
            "hints": {"bio": f"📏 {bio['height']}\" | {bio['bats']}/{bio['throws']}", "origin": f"🌎 {bio['birthCity']}, {bio['birthState']}"}
        })
        
        if i < 8:
            p_seasons = app_df[app_df['playerID'] == curr_pid][['yearID', 'teamID']]
            teammates = app_df.merge(p_seasons, on=['yearID', 'teamID'], suffixes=('','_t'))
            teammates = teammates[teammates['playerID'] != curr_pid]
            cands = teammates[(teammates['playerID'].map(player_primary) == pos_list[i+1]) & (teammates['playerID'].map(as_counts).fillna(0) >= d["threshold"])]
            if cands.empty: cands = teammates[teammates['playerID'].map(player_primary) == pos_list[i+1]]
            row = cands.sample(1).iloc[0]
            curr_pid, next_conn = row['playerID'], {"year": row['yearID'], "team": recent_teams.get(row['teamID'])}
    return chain

# --- 3. UI SETUP ---
st.set_page_config(page_title="Full Count", layout="wide", page_icon="⚾")

if 'chain' not in st.session_state:
    st.session_state.chain = generate_chain()
    st.session_state.idx, st.session_state.outs, st.session_state.h_count = 0, 0, 0
    st.session_state.res, st.session_state.over, st.session_state.rev = [], False, False
    st.session_state.s_t, st.session_state.s_b, st.session_state.s_o = False, False, False

d = st.session_state.chain[0]['diff']

st.markdown(f"""<style>
    [data-testid="stSidebar"] {{ background-color: #0e1117; border-right: 1px solid #333; }}
    .at-bat-card {{ background-color: #161b22; color: white; padding: 30px; border-radius: 12px; border: 1px solid #30363d; border-top: 5px solid {d['clr']}; }}
    .out-dot {{ height: 16px; width: 16px; background-color: #21262d; border-radius: 50%; display: inline-block; margin-right: 6px; border: 1px solid #30363d; }}
    .out-filled {{ background-color: #ff4b4b !important; box-shadow: 0 0 8px #ff4b4b; }}
    .stat-text {{ font-family: 'Courier New', monospace; color: {d['clr']}; font-size: 1.1em; letter-spacing: 0.5px; }}
</style>""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: white; letter-spacing: 2px;'>FULL COUNT</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{d['clr']}; text-align: center; font-weight:bold; font-size: 0.8em;'>{d['lbl']}</p>", unsafe_allow_html=True)
    st.divider()
    
    st.write("### LINEUP PROGRESS")
    for i in range(9):
        status = st.session_state.res[i] if i < len(st.session_state.res) else ("👉" if i == st.session_state.idx else "⚪")
        st.write(f"{status} **{st.session_state.chain[i]['pos']}**")
    
    st.divider()
    st.write(f"**Total Hints:** `{st.session_state.h_count}`")
    if st.button("Reset Daily Game"): 
        st.session_state.clear()
        st.rerun()

# --- MAIN AREA ---
if not st.session_state.over:
    curr = st.session_state.chain[st.session_state.idx]
    
    col_header, col_outs = st.columns([3, 1])
    with col_header:
        st.subheader(f"Inning {st.session_state.idx + 1} / 9")
    with col_outs:
        o_html = "".join([f'<span class="out-dot {"out-filled" if i < st.session_state.outs else ""}"></span>' for i in range(3)])
        st.markdown(f"<div style='text-align:right;'>{o_html}</div>", unsafe_allow_html=True)

    if st.session_state.outs >= 3:
        st.error(f"STRIKE THREE! Game Over. The player was **{curr['name']}**.")
        while len(st.session_state.res) < 9: st.session_state.res.append("🟥")
        st.session_state.over = True
        st.rerun()

    # THE AT-BAT CARD
    st.markdown(f"""<div class="at-bat-card">
        <h1 style='margin-top:0; color:white;'>{curr['pos']}</h1>
        <p style='color:#8b949e; font-size:1.1em;'>{ "Start the chain with this featured player." if st.session_state.idx == 0 else f"Teammate connection: <b>{curr['year']} {curr['team']}</b>"}</p>
        <p class="stat-text">{curr['report']}</p>
    </div>""", unsafe_allow_html=True)
    
    st.write("")

    # GUESSING
    c1, c2 = st.columns([3, 1])
    with c1:
        if not st.session_state.rev:
            with st.form("guess_form", clear_on_submit=True):
                pick = st.selectbox("Search MLB Database:", [""] + sorted(list(name_to_id.keys())), label_visibility="collapsed")
                if st.form_submit_button("Submit Guess", use_container_width=True):
                    if pick == curr['name']:
                        st.session_state.res.append("🟩")
                        st.session_state.idx += 1
                        st.session_state.s_t = st.session_state.s_b = st.session_state.s_o = False
                        if st.session_state.idx == 9: st.session_state.over = True
                    else: st.session_state.outs += 1
                    st.rerun()
        else:
            st.warning(f"MANAGER REVEAL: **{curr['name']}**")
            if st.button("Advance to Next Inning", use_container_width=True):
                st.session_state.rev = st.session_state.s_t = st.session_state.s_b = st.session_state.s_o = False
                st.session_state.idx += 1
                if st.session_state.idx == 9: st.session_state.over = True
                st.rerun()

    with c2:
        if st.button("Reveal Player", use_container_width=True, help="Costs 1 Out"):
            st.session_state.outs += 1; st.session_state.res.append("🟨"); st.session_state.rev = True; st.rerun()

    # HINTS
    st.write("### HINTS")
    h1, h2, h3 = st.columns(3)
    if h1.button("🏢 Career Teams", use_container_width=True): st.session_state.h_count += 1; st.session_state.s_t = True; st.rerun()
    if h2.button("👤 Bio Details", use_container_width=True): st.session_state.h_count += 1; st.session_state.s_b = True; st.rerun()
    if h3.button("🏠 Home Town", use_container_width=True): st.session_state.h_count += 1; st.session_state.s_o = True; st.rerun()

    if st.session_state.s_t:
        t_ids = app_df[app_df['playerID'] == curr['pid']]['teamID'].unique()
        st.info(f"Teams: {', '.join(sorted([recent_teams.get(tid) for tid in t_ids if recent_teams.get(tid)]))}")
    if st.session_state.s_b: st.info(f"Physicals: {curr['hints']['bio']}")
    if st.session_state.s_o: st.info(f"Birthplace: {curr['hints']['origin']}")

else:
    st.balloons()
    st.success("## FINAL BOX SCORE")
    st.write(f"Outs: **{st.session_state.outs}** | Hints: **{st.session_state.h_count}**")
    
    for p in st.session_state.chain:
        st.write(f"**{p['pos']}:** {p['name']}")
    
    if st.button("New Game"): 
        st.session_state.clear()
        st.rerun()