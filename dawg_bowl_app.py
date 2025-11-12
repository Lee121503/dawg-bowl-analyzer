import streamlit as st
import streamlit_authenticator as stauth
import yaml
import pandas as pd
import re
from fuzzywuzzy import fuzz
from utils.draft_helpers import calculate_adp

# --- Streamlit layout ---
st.set_page_config(layout="wide")

# --- Utility functions ---
def clean_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def is_fuzzy_match(name, name_list, threshold=90):
    return any(fuzz.ratio(name, target) >= threshold for target in name_list)

# --- AUTHENTICATION CONFIG ---
config_yaml = """
credentials:
  usernames:
    Lee121503:
      name: Chad
      password: Lee1215032025
    D4ve:
      name: Dave
      password: D4ve2025
    CGEEEEEE:
      name: Chris
      password: CGEEEEEE2025
    Nez:
      name: Andrew
      password: Nez2025
    Wutang:
      name: Matt
      password: Wutang2025

cookie:
  name: dawg_bowl
  key: abcdef
  expiry_days: 1
"""

# --- Load Config and Initialize Authenticator ---
config = yaml.safe_load(config_yaml)
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- Login Widget ---
name, auth_status, username = authenticator.login(
    fields={'Form name': 'Login'},
    location='main'
)

# --- Logout Button ---
authenticator.logout('Logout', location='sidebar')

# --- Authenticated Block ---
if auth_status:
    st.success(f"Welcome {name} 👋")

    # --- Week selector ---
    week_options = {
        "Week 9": "week9_drafts.csv",
        "Week 10": "week10_drafts.csv",
        "Week 11": "week11_drafts.csv"
    }

    selected_week_label = st.selectbox(
        "Select Week",
        list(week_options.keys()),
        index=list(week_options.keys()).index("Week 11")
    )
    selected_week_file = week_options[selected_week_label]

    st.title(f"Dawg Bowl Contest Dashboard — {selected_week_label}")

    # --- Load and normalize draft data ---
    df = pd.read_csv(f"data/{selected_week_file}", sep=None, engine="python")
    if "Team" in df.columns and "NFL_Team" not in df.columns:
        df = df.rename(columns={"Team": "NFL_Team"})
    df["CleanPlayer"] = df["Player"].apply(clean_name)

    # --- Shared Filters ---
    all_positions = sorted(df["Position"].dropna().unique())
    shared_positions = st.multiselect("Filter by Position (shared)", all_positions, default=all_positions, key="shared_position_filter")

    adp_min, adp_max = df["Pick"].min(), df["Pick"].max()
    shared_adp_range = st.slider("Filter by ADP Range (shared)", float(adp_min), float(adp_max), (float(adp_min), float(adp_max)), key="shared_adp_filter")

    if st.button("🔄 Reset Filters"):
        st.experimental_rerun()

    # --- Tab Layout ---
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "📋 Draft Viewer",
        "📋 Player Dashboard",
        "🔍 Combo Finder",
        "🤝 Co-Drafted Dashboard",
        "📊 User Exposure Dashboard",
        "🧠 User Similarity Dashboard",
        "🩹 Injury Swap",
        "📈 ETR Leaderboard",
        "📊 ETR Impact Dashboard",
        "📉 ADP Change Tracker"
    ])

    # --- Tab 1: Draft Viewer ---
    with tab1:
        st.subheader("📋 Draft Viewer")
    
        all_users = sorted(df["User"].dropna().unique())
        selected_user = st.selectbox("Filter by User", ["All Users"] + all_users, key="tab1_user")
    
        if selected_user != "All Users":
            user_drafts = df[df["User"] == selected_user]["Draft"].unique()
            st.markdown(f"**Drafts for `{selected_user}`:** {sorted(user_drafts)}")
            filtered_df = df[df["Draft"].isin(user_drafts)]
        else:
            filtered_df = df.copy()
    
        all_drafts = sorted(filtered_df["Draft"].unique())
        selected_draft = st.selectbox("Select Draft Number", all_drafts, key="tab1_draft")
    
        draft_df = filtered_df[filtered_df["Draft"] == selected_draft]
    
        team_groups = draft_df.groupby("Team")
        for team_num, group in team_groups:
            st.markdown(f"### 🏈 Team {team_num} — User: `{group['User'].iloc[0]}`")
            team_df = group[["Player", "Position", "Team", "Pick"]].sort_values("Pick")
            st.dataframe(team_df, use_container_width=True)

    # --- Tab 2: Player Dashboard ---
    with tab2:
        st.subheader("📋 Player Dashboard")
    
        adp_df = calculate_adp(df).round(2)
        total_drafts = df["Draft"].nunique()
    
        position_map = df[["Player", "Position"]].drop_duplicates()
        team_map = df[["Player", "NFL_Team"]].drop_duplicates()
    
        pick_stats = df.groupby("Player")["Pick"].agg(["count", "min", "max"]).reset_index()
        pick_stats.columns = ["Player", "Times Drafted", "Earliest Pick", "Latest Pick"]
    
        dashboard_df = adp_df.merge(position_map, on="Player", how="left")
        dashboard_df = dashboard_df.merge(team_map, on="Player", how="left")
        dashboard_df = dashboard_df.merge(pick_stats, on="Player", how="left")
        dashboard_df["Exposure"] = (dashboard_df["Times Drafted"] / total_drafts * 100).round(2)
    
        # Stack Rate
        stack_counts = []
        for (draft_id, team_id), group in df.groupby(["Draft", "Team"]):
            nfl_team_map = group.set_index("Player")["NFL_Team"].to_dict()
            players = list(nfl_team_map.keys())
            for player in players:
                player_team = nfl_team_map[player]
                teammates = [p for p in players if p != player and nfl_team_map[p] == player_team]
                stack_counts.append({
                    "Player": player,
                    "Draft": draft_id,
                    "Is_Stacked": len(teammates) > 0
                })
    
        stack_df = pd.DataFrame(stack_counts)
        stack_rate = stack_df.groupby("Player")["Is_Stacked"].mean().reset_index()
        stack_rate["Stack Rate"] = (stack_rate["Is_Stacked"] * 100).round(2)
        dashboard_df = dashboard_df.merge(stack_rate[["Player", "Stack Rate"]], on="Player", how="left")
    
        # Load UD IDs
        try:
            ud_df = pd.read_csv("data/week11UD.csv", usecols=[0, 1, 2], names=["id", "First", "Last"], header=0)
            ud_df["FullName"] = (ud_df["First"].str.strip() + " " + ud_df["Last"].str.strip()).str.strip()
            ud_df["CleanPlayer"] = ud_df["FullName"].apply(clean_name)
            dashboard_df["CleanPlayer"] = dashboard_df["Player"].apply(clean_name)
            dashboard_df = dashboard_df.merge(ud_df[["CleanPlayer", "id"]], on="CleanPlayer", how="left")
        except FileNotFoundError:
            st.warning("UD ID file not found. Player IDs will be missing.")
            dashboard_df["id"] = None
    
        # Filters
        positions = sorted(dashboard_df["Position"].dropna().unique())
        selected_positions = st.multiselect("Filter by Position", positions, default=positions, key="tab2_position")
    
        adp_min, adp_max = dashboard_df["Average Draft Position"].min(), dashboard_df["Average Draft Position"].max()
        adp_range = st.slider("Filter by ADP Range", float(adp_min), float(adp_max), (float(adp_min), float(adp_max)), key="tab2_adp")
    
        all_users = sorted(df["User"].dropna().unique())
        selected_user = st.selectbox("Filter by User (optional)", ["All Users"] + all_users, key="tab2_user")
    
        filtered_df = dashboard_df[
            (dashboard_df["Position"].isin(selected_positions)) &
            (dashboard_df["Average Draft Position"] >= adp_range[0]) &
            (dashboard_df["Average Draft Position"] <= adp_range[1])
        ]
    
        if selected_user != "All Users":
            user_draft_counts = df.groupby("User")["Draft"].nunique().reset_index()
            user_draft_counts.columns = ["User", "User Drafts"]
            user_player_counts = df.groupby(["User", "Player"])["Draft"].nunique().reset_index()
            user_player_counts.columns = ["User", "Player", "Player Drafts"]
            user_exposure_df = pd.merge(user_player_counts, user_draft_counts, on="User")
            user_exposure_df["User Exposure %"] = (user_exposure_df["Player Drafts"] / user_exposure_df["User Drafts"] * 100).round(2)
            user_exposure_df = user_exposure_df[user_exposure_df["User"] == selected_user]
            filtered_df = pd.merge(filtered_df, user_exposure_df[["Player", "User Exposure %"]], on="Player", how="inner")
    
        display_cols = [
            "id", "Player", "Position", "NFL_Team", "Average Draft Position",
            "Earliest Pick", "Latest Pick", "Exposure", "Stack Rate"
        ]
        if "User Exposure %" in filtered_df.columns:
            display_cols.insert(display_cols.index("Stack Rate"), "User Exposure %")
    
        filtered_df = filtered_df[display_cols]
        display_cols_for_table = [col for col in display_cols if col != "id"]
    
        st.write(f"Filtered rows: {len(filtered_df)}")
    
        if not filtered_df.empty:
            sorted_df = filtered_df.sort_values("Average Draft Position")
            st.dataframe(sorted_df[display_cols_for_table], use_container_width=True)
    
            csv_bytes = sorted_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download CSV (with id)",
                data=csv_bytes,
                file_name=f"{selected_week_label.replace(' ', '_')}_PlayerDashboard.csv",
                mime="text/csv",
                key="tab2_download"
            )
        else:
            st.warning("No players match the current filters.")
 
    # --- Tab 3: Combo Finder ---
    with tab3:
        st.subheader("🔍 Combo Finder")
    
        selected_user = st.selectbox("Filter by User", ["All Users"] + all_users, key="tab3_user")
    
        if selected_user != "All Users":
            user_teams = df[df["User"] == selected_user][["Draft", "Team"]].drop_duplicates()
            combo_base_df = pd.merge(df, user_teams, on=["Draft", "Team"])
        else:
            combo_base_df = df.copy()
    
        combo_df = combo_base_df[
            (combo_base_df["Position"].isin(shared_positions)) &
            (combo_base_df["Pick"] >= shared_adp_range[0]) &
            (combo_base_df["Pick"] <= shared_adp_range[1])
        ]
    
        combo_pairs = []
        for (draft_id, team_id), group in combo_df.groupby(["Draft", "Team"]):
            player_team_map = group.set_index("Player")["NFL_Team"].to_dict()
            pick_lookup = group.set_index("Player")["Pick"].to_dict()
            players = sorted(player_team_map.keys())
            for i in range(len(players)):
                for j in range(i + 1, len(players)):
                    combo_pairs.append({
                        "Player A": players[i],
                        "Player B": players[j],
                        "Team A": player_team_map[players[i]],
                        "Team B": player_team_map[players[j]],
                        "ADP A": pick_lookup.get(players[i], None),
                        "ADP B": pick_lookup.get(players[j], None)
                    })
    
        combo_df = pd.DataFrame(combo_pairs)
        combo_df["Is_Teammate"] = combo_df["Team A"] == combo_df["Team B"]
    
        combo_summary = combo_df.groupby(["Player A", "Player B", "Is_Teammate"]).agg({
            "ADP A": "mean",
            "ADP B": "mean"
        }).reset_index()
    
        combo_summary["Times Drafted Together"] = combo_df.groupby(["Player A", "Player B", "Is_Teammate"]).size().values
        combo_summary["Exposure %"] = (combo_summary["Times Drafted Together"] / combo_base_df["Draft"].nunique() * 100).round(2)
        combo_summary["ADP A"] = combo_summary["ADP A"].round(2)
        combo_summary["ADP B"] = combo_summary["ADP B"].round(2)
    
        player_search = st.text_input("Search for combos involving a specific player (optional)", key="tab3_search")
        if player_search:
            clean_search = clean_name(player_search)
            combo_summary = combo_summary[
                combo_summary["Player A"].apply(clean_name).eq(clean_search) |
                combo_summary["Player B"].apply(clean_name).eq(clean_search)
            ]
    
        min_combo_count = st.slider("Minimum Times Drafted Together", 1, 10, 2, key="tab3_min_count")
        filtered = combo_summary[combo_summary["Times Drafted Together"] >= min_combo_count]
    
        st.write(f"Filtered combos: {len(filtered)}")
    
        view_mode = st.radio("View mode", ["Table", "Editor"], horizontal=True, key="tab3_view_mode")
    
        st.markdown("### 🧩 All Combos")
        if not filtered.empty:
            all_combo_df = filtered.sort_values("Times Drafted Together", ascending=False)
            if view_mode == "Table":
                st.dataframe(all_combo_df, use_container_width=True)
            else:
                st.data_editor(
                    all_combo_df,
                    use_container_width=True,
                    height=900,
                    column_config={
                        "Times Drafted Together": st.column_config.NumberColumn(format="%d"),
                        "Exposure %": st.column_config.NumberColumn(format="%.2f"),
                        "ADP A": st.column_config.NumberColumn(format="%.2f"),
                        "ADP B": st.column_config.NumberColumn(format="%.2f")
                    }
                )
        else:
            st.warning("No combos match the current filters.")
    
        st.markdown("### 🚫 Non-Teammate Combos")
        non_teammates = filtered[filtered["Is_Teammate"] == False]
        if not non_teammates.empty:
            non_teammates_df = non_teammates.sort_values("Times Drafted Together", ascending=False)
            if view_mode == "Table":
                st.dataframe(non_teammates_df, use_container_width=True)
            else:
                st.data_editor(
                    non_teammates_df,
                    use_container_width=True,
                    height=900,
                    column_config={
                        "Times Drafted Together": st.column_config.NumberColumn(format="%d"),
                        "Exposure %": st.column_config.NumberColumn(format="%.2f"),
                        "ADP A": st.column_config.NumberColumn(format="%.2f"),
                        "ADP B": st.column_config.NumberColumn(format="%.2f")
                    }
                )
        else:
            st.info("No non-teammate combos found at this frequency.")
 
    # --- Tab 4: Co-Drafted Dashboard ---
    with tab4:
        st.subheader("Co-Drafted Player Dashboard")
    
        all_players = sorted(df["Player"].dropna().unique())
        selected_players = st.multiselect("Select 1–3 Anchor Players", all_players, max_selections=3, key="tab4_anchors")
    
        if selected_players:
            team_picks = df.groupby(["Draft", "Team"])["Player"].apply(list).reset_index()
            team_picks["Has Combo"] = team_picks["Player"].apply(lambda picks: all(p in picks for p in selected_players))
            matching_teams = team_picks[team_picks["Has Combo"]]
    
            if not matching_teams.empty:
                all_coplayers = []
                for picks in matching_teams["Player"]:
                    all_coplayers.extend(picks)
                coplayer_counts = pd.Series(all_coplayers)
                coplayer_counts = coplayer_counts[~coplayer_counts.isin(selected_players)]
                coplayer_summary = coplayer_counts.value_counts().reset_index()
                coplayer_summary.columns = ["Player", "Times Co-Drafted"]
    
                position_map = df[["Player", "Position"]].drop_duplicates()
                team_map = df[["Player", "NFL_Team"]].drop_duplicates()
                adp_df = calculate_adp(df).round(2)
    
                coplayer_summary = coplayer_summary.merge(position_map, on="Player", how="left")
                coplayer_summary = coplayer_summary.merge(team_map, on="Player", how="left")
                coplayer_summary = coplayer_summary.merge(adp_df, on="Player", how="left")
    
                coplayer_summary = coplayer_summary[coplayer_summary["Position"].isin(shared_positions)]
                coplayer_summary = coplayer_summary[[
                    "Player", "Position", "NFL_Team", "Average Draft Position", "Times Co-Drafted"
                ]].sort_values("Times Co-Drafted", ascending=False)
    
                st.dataframe(coplayer_summary, use_container_width=True)
            else:
                st.info("No teams drafted all selected players together.")

    # --- Tab 5: User Exposure Dashboard ---
    with tab5:
        st.subheader("📊 User Exposure Dashboard")
    
        selected_users = st.multiselect(
            "Select Users",
            sorted(df["User"].dropna().unique()),
            default=[],
            key="tab5_users"
        )
    
        if selected_users:
            exposure_df = df[df["User"].isin(selected_users)]
        else:
            exposure_df = df.copy()
    
        user_draft_counts = exposure_df.groupby("User")["Draft"].nunique().reset_index()
        user_draft_counts.columns = ["User", "User Drafts"]
    
        user_player_counts = exposure_df.groupby(["User", "Player"])["Draft"].nunique().reset_index()
        user_player_counts.columns = ["User", "Player", "Player Drafts"]
    
        exposure_summary = pd.merge(user_player_counts, user_draft_counts, on="User")
        exposure_summary["User Exposure %"] = (exposure_summary["Player Drafts"] / exposure_summary["User Drafts"] * 100).round(2)
    
        min_exposure = st.slider("Minimum Exposure %", 0.0, 100.0, 5.0, key="tab5_min_exposure")
        filtered_df = exposure_summary[exposure_summary["User Exposure %"] >= min_exposure]
    
        st.write(f"Filtered rows: {len(filtered_df)}")
    
        view_mode = st.radio("View mode", ["Table", "Editor"], horizontal=True, key="tab5_view_mode")
    
        if not filtered_df.empty:
            sorted_df = filtered_df.sort_values("User Exposure %", ascending=False)
            if view_mode == "Table":
                st.dataframe(sorted_df, use_container_width=True)
            else:
                st.data_editor(
                    sorted_df,
                    use_container_width=True,
                    height=900,
                    column_config={
                        "User Exposure %": st.column_config.NumberColumn(format="%.2f"),
                        "Player Drafts": st.column_config.NumberColumn(format="%d"),
                        "User Drafts": st.column_config.NumberColumn(format="%d")
                    }
                )
        else:
            st.warning("No exposure data matches the current filters.")
 
    # --- Tab 6: User Similarity Dashboard ---
    with tab6:
        st.subheader("🧠 User Similarity Dashboard")
    
        user_player_counts = df.groupby(["User", "Player"])["Draft"].nunique().unstack(fill_value=0)
        user_draft_totals = df.groupby("User")["Draft"].nunique()
        exposure_matrix = user_player_counts.div(user_draft_totals, axis=0) * 100
    
        from sklearn.metrics.pairwise import cosine_similarity
        similarity_matrix = pd.DataFrame(
            cosine_similarity(exposure_matrix),
            index=exposure_matrix.index,
            columns=exposure_matrix.index
        )
    
        selected_user = st.selectbox("Select User to Compare", sorted(similarity_matrix.index), key="tab6_user")
        min_similarity = st.slider("Minimum Similarity Score", 0.0, 1.0, 0.5, key="tab6_min_similarity")
        view_mode = st.radio("View mode", ["Table", "Editor"], horizontal=True, key="tab6_view_mode")
    
        similarity_scores = similarity_matrix[selected_user].drop(selected_user).reset_index()
        similarity_scores.columns = ["User", "Similarity Score"]
        similarity_scores = similarity_scores.sort_values("Similarity Score", ascending=False)
        filtered_scores = similarity_scores[similarity_scores["Similarity Score"] >= min_similarity]
    
        st.write(f"Users similar to `{selected_user}`: {len(filtered_scores)}")
    
        if not filtered_scores.empty:
            if view_mode == "Table":
                st.dataframe(filtered_scores, use_container_width=True)
            else:
                st.data_editor(
                    filtered_scores,
                    use_container_width=True,
                    height=900,
                    column_config={
                        "Similarity Score": st.column_config.NumberColumn(format="%.3f")
                    }
                )
        else:
            st.info("No users meet the similarity threshold.")
  
    # --- Tab 7: Injury Swap Dashboard ---
    with tab7:
        st.subheader(f"🩹 Injury Swap Tool — {selected_week_label}")
    
        injury_file_map = {
            "Week 9": "Week9UD.csv",
            "Week 10": "week10UD.csv",
            "Week 11": "week11UD.csv"
        }
        injury_file = injury_file_map.get(selected_week_label, "week10UD.csv")
        injury_df = pd.read_csv(f"data/{injury_file}")
    
        try:
            etr_df = pd.read_csv("data/ETR Projections.csv")
        except FileNotFoundError:
            etr_df = pd.DataFrame(columns=["Player", "Pos", "Half PPR Proj", "FD Ceiling", "Slate"])
            st.warning("ETR projections not yet available.")
    
        injury_df["CleanStatus"] = injury_df["lineupStatus"].fillna("").str.upper().str.strip()
        injury_df["CleanName"] = (
            injury_df["firstName"].str.strip() + " " + injury_df["lastName"].str.strip()
        ).apply(clean_name)
    
        if not etr_df.empty:
            main_slate = etr_df[etr_df["Slate"].str.upper() == "MAIN"]
            main_slate["Pos"] = main_slate["Pos"].str.upper().str.strip()
            main_slate = main_slate[["Player", "Pos", "Half PPR Proj", "FD Ceiling"]].dropna()
            main_slate["CleanPlayer"] = main_slate["Player"].apply(clean_name)
    
            rankings = (
                main_slate.sort_values("Half PPR Proj", ascending=False)
                .groupby("Pos")["CleanPlayer"]
                .apply(list)
                .to_dict()
            )
        else:
            rankings = {}
    
        def tag_flex_players(team_df):
            team_df = team_df.sort_values("Pick").copy()
            pos_counts = {"RB": 0, "WR": 0, "TE": 0}
            flex_flags = []
            for _, row in team_df.iterrows():
                pos = row["Position"]
                if pos not in pos_counts:
                    flex_flags.append(False)
                    continue
                pos_counts[pos] += 1
                if (pos == "RB" and pos_counts[pos] == 2) or \
                   (pos == "WR" and pos_counts[pos] == 3) or \
                   (pos == "TE" and pos_counts[pos] == 2):
                    flex_flags.append(True)
                else:
                    flex_flags.append(False)
            team_df["IsFlex"] = flex_flags
            return team_df
    
        df["CleanPlayer"] = df["Player"].apply(clean_name)
        df = df.groupby(["Draft", "Team"]).apply(tag_flex_players).reset_index(drop=True)
    
        user = st.selectbox("Select a user", df["User"].unique(), key="tab7_user")
        user_drafts = df[df["User"] == user]
        user_clean_names = set(user_drafts["CleanPlayer"])
    
        st.subheader("QUESTIONABLE Players — Manual Override")
        questionable_df = injury_df[
            (injury_df["CleanStatus"] == "QUESTIONABLE") &
            (injury_df["CleanName"].apply(lambda x: is_fuzzy_match(x, user_clean_names)))
        ].copy()
    
        if "manual_out" not in st.session_state:
            st.session_state.manual_out = set()
    
        for _, row in questionable_df.iterrows():
            full_name = f"{row['firstName'].strip()} {row['lastName'].strip()}"
            clean = row["CleanName"]
            slot = row.get("slotName", "Unknown")
            toggle = st.toggle(f"{full_name} ({slot})", value=False, key=f"tab7_toggle_{clean}")
            if toggle:
                st.session_state.manual_out.add(clean)
            else:
                st.session_state.manual_out.discard(clean)
    
        manual_text = st.text_input("Manually mark a player OUT (e.g. Tyreek Hill)", key="tab7_manual_text")
        if manual_text:
            st.session_state.manual_out.add(clean_name(manual_text))
    
        if st.session_state.manual_out:
            st.subheader("Manually Added OUT Players")
            to_remove = set()
            for name in sorted(st.session_state.manual_out):
                if not st.checkbox(f"{name}", value=True, key=f"tab7_manual_{name}"):
                    to_remove.add(name)
            st.session_state.manual_out -= to_remove
    
        injured_df = injury_df[injury_df["CleanStatus"].isin(["OUT", "DOUBTFUL"])].copy()
        drafted_names = set(df["CleanPlayer"])
        out_players = {}
        for pos in injured_df["slotName"].dropna().unique():
            injured_at_pos = injured_df[injured_df["slotName"] == pos]
            filtered = injured_at_pos[injured_at_pos["CleanName"].apply(lambda x: is_fuzzy_match(x, drafted_names))]
            out_players[pos] = filtered["CleanName"].tolist()
    
        match_mode = st.radio("Replacement Match Mode", ["Fuzzy", "Exact"], horizontal=True, key="tab7_match_mode")
    
        flagged_drafts = []
        out_names = sum(out_players.values(), []) + list(st.session_state.manual_out)
        for draft_id in user_drafts["Draft"].unique():
            full_draft = df[df["Draft"] == draft_id]
            user_picks = user_drafts[user_drafts["Draft"] == draft_id]
            user_out_picks = user_picks[user_picks["CleanPlayer"].apply(lambda x: is_fuzzy_match(x, out_names))]
            if not user_out_picks.empty:
                flagged_drafts.append((draft_id, full_draft, user_out_picks))
    
        st.write(f"Flagged drafts with OUT players: {len(flagged_drafts)}")
 
    # --- Tab 8: ETR Leaderboard ---
    with tab8:
        st.subheader("📈 ETR Leaderboard")
    
        try:
            etr_df = pd.read_csv("data/ETR Projections.csv")
        except FileNotFoundError:
            st.warning("ETR projections file not found.")
            etr_df = pd.DataFrame(columns=["Player", "Pos", "Half PPR Proj", "FD Ceiling", "Slate"])
    
        if not etr_df.empty:
            etr_df["CleanPlayer"] = etr_df["Player"].apply(clean_name)
            etr_df["Pos"] = etr_df["Pos"].str.upper().str.strip()
            etr_df = etr_df[["Player", "Pos", "Half PPR Proj", "FD Ceiling", "Slate"]].dropna()
    
            main_slate_df = etr_df[etr_df["Slate"].str.upper() == "MAIN"]
            sorted_df = main_slate_df.sort_values("Half PPR Proj", ascending=False)
    
            st.dataframe(sorted_df, use_container_width=True)
        else:
            st.info("No ETR projection data available.")
    
    # --- Tab 9: ETR Impact Dashboard ---
    with tab9:
        st.subheader("📊 ETR Impact Dashboard")
    
        try:
            etr_df = pd.read_csv("data/ETR Projections.csv")
        except FileNotFoundError:
            st.warning("ETR projections file not found.")
            etr_df = pd.DataFrame(columns=["Player", "Pos", "Half PPR Proj", "FD Ceiling", "Slate"])
    
        if not etr_df.empty:
            etr_df["CleanPlayer"] = etr_df["Player"].apply(clean_name)
            etr_df["Pos"] = etr_df["Pos"].str.upper().str.strip()
            etr_df = etr_df[["Player", "Pos", "Half PPR Proj", "FD Ceiling", "Slate"]].dropna()
    
            main_slate_df = etr_df[etr_df["Slate"].str.upper() == "MAIN"]
            main_slate_df["CleanPlayer"] = main_slate_df["Player"].apply(clean_name)
    
            df["CleanPlayer"] = df["Player"].apply(clean_name)
            merged_df = df.merge(main_slate_df[["CleanPlayer", "Half PPR Proj", "FD Ceiling"]], on="CleanPlayer", how="left")
    
            user_proj = merged_df.groupby("User")[["Half PPR Proj", "FD Ceiling"]].mean().reset_index()
            user_proj = user_proj.round(2).sort_values("Half PPR Proj", ascending=False)
    
            st.dataframe(user_proj, use_container_width=True)
        else:
            st.info("No ETR projection data available.")

    # --- Tab 10: Visual Insights Dashboard ---
    with tab10:
        st.subheader("📉 ADP Change Tracker")

        with st.expander("ℹ️ What do these terms mean?"):
            st.markdown("""
            - **Recent ADP**: The average draft position of a player over the most recent set of drafts you selected.
            - **Earlier ADP**: The average draft position of the same player from the previous set of drafts (same size window).
            - **ADP Change**: The difference between Earlier ADP and Recent ADP. A **positive** value means the player is being drafted **later** (falling), while a **negative** value means the player is being drafted **earlier** (rising).
            - **Velocity**: The rate of ADP change per draft. It helps identify how quickly a player's draft position is shifting.
            """)
       
        total_drafts = df["Draft"].nunique()
        max_range = min(20, total_drafts)
        draft_window = st.slider("Number of Recent Drafts to Compare", 2, max_range, 5, key="tab10_window")
    
        sorted_drafts = sorted(df["Draft"].unique())
        recent_drafts = sorted_drafts[-draft_window:]
        earlier_drafts = sorted_drafts[-(2 * draft_window):-draft_window] if len(sorted_drafts) >= 2 * draft_window else []
    
        adp_recent = df[df["Draft"].isin(recent_drafts)].groupby("Player")["Pick"].mean().reset_index()
        adp_recent.columns = ["Player", "Recent ADP"]
    
        adp_earlier = df[df["Draft"].isin(earlier_drafts)].groupby("Player")["Pick"].mean().reset_index()
        adp_earlier.columns = ["Player", "Earlier ADP"]
    
        adp_change = pd.merge(adp_recent, adp_earlier, on="Player", how="inner")
        adp_change["ADP Change"] = (adp_change["Earlier ADP"] - adp_change["Recent ADP"]).round(2)
        adp_change["Velocity"] = (adp_change["ADP Change"] / draft_window).round(2)
    
        position_map = df[["Player", "Position"]].drop_duplicates()
        team_map = df[["Player", "NFL_Team"]].drop_duplicates()
        adp_change = adp_change.merge(position_map, on="Player", how="left")
        adp_change = adp_change.merge(team_map, on="Player", how="left")
    
        selected_positions = st.multiselect("Filter by Position", sorted(df["Position"].dropna().unique()), default=sorted(df["Position"].dropna().unique()), key="tab10_position")
        adp_change = adp_change[adp_change["Position"].isin(selected_positions)]
    
        min_velocity = st.slider("Minimum Velocity of Change", 0.0, 5.0, 0.5, step=0.1, key="tab10_velocity")
        filtered_df = adp_change[adp_change["Velocity"].abs() >= min_velocity]
    
        st.write(f"Filtered players: {len(filtered_df)}")
    
        view_mode = st.radio("View mode", ["Table", "Editor"], horizontal=True, key="tab10_view_mode")
    
        if not filtered_df.empty:
            sorted_df = filtered_df.sort_values("Velocity", ascending=False)
            if view_mode == "Table":
                st.dataframe(sorted_df, use_container_width=True)
            else:
                st.data_editor(
                    sorted_df,
                    use_container_width=True,
                    height=900,
                    column_config={
                        "Recent ADP": st.column_config.NumberColumn(format="%.2f"),
                        "Earlier ADP": st.column_config.NumberColumn(format="%.2f"),
                        "ADP Change": st.column_config.NumberColumn(format="%.2f"),
                        "Velocity": st.column_config.NumberColumn(format="%.2f")
                    }
                )
        else:
            st.warning("No players meet the current filters.")

else:
    st.warning("Please log in to access the dashboard.")
