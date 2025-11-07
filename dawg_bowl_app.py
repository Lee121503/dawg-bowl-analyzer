import streamlit as st
import streamlit_authenticator as stauth
import yaml
from fuzzywuzzy import fuzz
import re

def clean_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", name)  # Remove suffixes
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def is_fuzzy_match(name, name_list, threshold=90):
    return any(fuzz.ratio(name, target) >= threshold for target in name_list)

# --- Set layout early ---
st.set_page_config(layout="wide")

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
authenticator.logout('Logout', location='sidebar')

if auth_status:
    st.success(f"Welcome {name} 👋")

    import pandas as pd
    from utils.draft_helpers import calculate_adp

    # --- Week selector ---
    week_options = {
        "Week 9": "week9_drafts.csv",
        "Week 10": "week10_drafts.csv"
    }

    selected_week_label = st.selectbox(
        "Select Week",
        list(week_options.keys()),
        index=list(week_options.keys()).index("Week 10")  # Default to Week 10
    )
    selected_week_file = week_options[selected_week_label]

    st.title(f"Dawg Bowl Contest Dashboard — {selected_week_label}")

    # --- Load and normalize draft data ---
    df = pd.read_csv(f"data/{selected_week_file}", sep=None, engine="python")

    # Rename 'Team' to 'NFL_Team' for consistency
    if "Team" in df.columns and "NFL_Team" not in df.columns:
        df = df.rename(columns={"Team": "NFL_Team"})

    # Normalize player names
    df["CleanPlayer"] = df["Player"].apply(clean_name)

    # --- Shared Filters (now safe to use df) ---
    all_positions = sorted(df["Position"].dropna().unique())
    shared_positions = st.multiselect("Filter by Position (shared)", all_positions, default=all_positions, key="shared_position_filter")
    
    adp_min, adp_max = df["Pick"].min(), df["Pick"].max()
    shared_adp_range = st.slider("Filter by ADP Range (shared)", float(adp_min), float(adp_max), (float(adp_min), float(adp_max)), key="shared_adp_filter")
    
    if st.button("🔄 Reset Filters"):
        st.experimental_rerun()
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📋 Draft Viewer",
        "📋 Player Dashboard",
        "🔍 Combo Finder",
        "🤝 Co-Drafted Dashboard",
        "📊 User Exposure Dashboard",
        "🧠 User Similarity Dashboard",
        "🩹 Injury Swap",
        "📈 ETR Leaderboard",
        "📊 ETR Impact Dashboard"
    ])

    
    # --- Tab 1: Draft Viewer ---
    with tab1:
        st.subheader("📋 Draft Viewer")
    
        # --- Optional: Filter by User ---
        all_users = sorted(df["User"].dropna().unique())
        selected_user = st.selectbox("Filter by User", ["All Users"] + all_users)
    
        if selected_user != "All Users":
            user_drafts = df[df["User"] == selected_user]["Draft"].unique()
            st.markdown(f"**Drafts for `{selected_user}`:** {sorted(user_drafts)}")
            filtered_df = df[df["Draft"].isin(user_drafts)]
        else:
            filtered_df = df.copy()
    
        # --- Select a draft number ---
        all_drafts = sorted(filtered_df["Draft"].unique())
        selected_draft = st.selectbox("Select Draft Number", all_drafts)
    
        # --- Filter to selected draft ---
        draft_df = filtered_df[filtered_df["Draft"] == selected_draft]
    
        # --- Group by fantasy team and show players + user ---
        team_groups = draft_df.groupby("Team")
        for team_num, group in team_groups:
            st.markdown(f"### 🏈 Team {team_num} — User: `{group['User'].iloc[0]}`")
    
            team_df = group[["Player", "Position", "Team", "Pick"]].sort_values("Pick")
            styled_df = team_df.style.format({"Pick": "{:.2f}"}).background_gradient(subset=["Pick"], cmap="Blues")
    
            st.dataframe(styled_df, use_container_width=True)

    
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
    
        # --- Correct Stack Rate Calculation ---
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
    
        # --- Filters ---
        positions = sorted(dashboard_df["Position"].dropna().unique())
        selected_positions = st.multiselect("Filter by Position", positions, default=positions)
    
        adp_min, adp_max = dashboard_df["Average Draft Position"].min(), dashboard_df["Average Draft Position"].max()
        adp_range = st.slider("Filter by ADP Range", float(adp_min), float(adp_max), (float(adp_min), float(adp_max)))
    
        all_users = sorted(df["User"].dropna().unique())
        selected_user = st.selectbox("Filter by User (optional)", ["All Users"] + all_users)
    
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
            filtered_df = filtered_df[[
                "Player", "Position", "NFL_Team", "Average Draft Position", "Earliest Pick", "Latest Pick",
                "Exposure", "User Exposure %", "Stack Rate"
            ]]
        else:
            filtered_df = filtered_df[[
                "Player", "Position", "NFL_Team", "Average Draft Position", "Earliest Pick", "Latest Pick",
                "Exposure", "Stack Rate"
            ]]
    
        # --- Display ---
        st.write(f"Filtered rows: {len(filtered_df)}")
    
        gradient_cols = ["Average Draft Position", "Earliest Pick", "Latest Pick", "Exposure", "Stack Rate"]
        if "User Exposure %" in filtered_df.columns:
            gradient_cols.append("User Exposure %")
    
        view_mode = st.radio("View mode", ["Gradient", "Editor"], horizontal=True, key="dashboard_view_mode")
    
        if not filtered_df.empty:
            if view_mode == "Gradient":
                styled_df = filtered_df.sort_values("Average Draft Position").style.format({
                    col: "{:.2f}" for col in gradient_cols
                }).background_gradient(subset=gradient_cols, cmap="Blues")
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.data_editor(
                    filtered_df.sort_values("Average Draft Position"),
                    use_container_width=True,
                    height=900,
                    column_config={col: st.column_config.NumberColumn(format="%.2f") for col in gradient_cols}
                )
        else:
            st.warning("No players match the current filters. Try adjusting position, ADP range, or user.")
    
    # --- Tab 3: Combo Finder ---
    with tab3:
        st.subheader("🔍 Combo Finder")
    
        # --- User filter ---
        all_users = sorted(df["User"].dropna().unique())
        selected_user = st.selectbox("Filter by User", ["All Users"] + all_users, key="combo_user_filter")
    
        if selected_user != "All Users":
            user_teams = df[df["User"] == selected_user][["Draft", "Team"]].drop_duplicates()
            combo_base_df = pd.merge(df, user_teams, on=["Draft", "Team"])
        else:
            combo_base_df = df.copy()
    
        # --- Apply shared filters ---
        combo_df = combo_base_df[
            (combo_base_df["Position"].isin(shared_positions)) &
            (combo_base_df["Pick"] >= shared_adp_range[0]) &
            (combo_base_df["Pick"] <= shared_adp_range[1])
        ]
    
        # --- Build combos per fantasy team (Draft + Team) ---
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
    
        # --- Optional: Filter by Player Name ---
        player_search = st.text_input("Search for combos involving a specific player (optional)")
        if player_search:
            clean_search = clean_name(player_search)
            combo_summary = combo_summary[
                combo_summary["Player A"].apply(clean_name).eq(clean_search) |
                combo_summary["Player B"].apply(clean_name).eq(clean_search)
            ]
    
        # --- Filter by minimum frequency ---
        min_combo_count = st.slider("Minimum Times Drafted Together", 1, 10, 2)
        filtered = combo_summary[combo_summary["Times Drafted Together"] >= min_combo_count]
    
        st.write(f"Filtered combos: {len(filtered)}")
    
        view_mode = st.radio("View mode", ["Gradient", "Editor"], horizontal=True, key="combo_view_mode")
    
        # --- Table 1: All Combos ---
        st.markdown("### 🧩 All Combos")
        if not filtered.empty:
            all_combo_df = filtered.sort_values("Times Drafted Together", ascending=False)
            if view_mode == "Gradient":
                styled = all_combo_df.style.format({
                    "Times Drafted Together": "{:.0f}",
                    "Exposure %": "{:.2f}",
                    "ADP A": "{:.2f}",
                    "ADP B": "{:.2f}"
                }).background_gradient(subset=["Times Drafted Together", "Exposure %", "ADP A", "ADP B"], cmap="Blues")
                st.dataframe(styled, use_container_width=True)
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
    
        # --- Table 2: Non-Teammate Combos ---
        st.markdown("### 🚫 Non-Teammate Combos")
        non_teammates = filtered[filtered["Is_Teammate"] == False]
        if not non_teammates.empty:
            non_teammates_df = non_teammates.sort_values("Times Drafted Together", ascending=False)
            if view_mode == "Gradient":
                styled = non_teammates_df.style.format({
                    "Times Drafted Together": "{:.0f}",
                    "Exposure %": "{:.2f}",
                    "ADP A": "{:.2f}",
                    "ADP B": "{:.2f}"
                }).background_gradient(subset=["Times Drafted Together", "Exposure %", "ADP A", "ADP B"], cmap="Oranges")
                st.dataframe(styled, use_container_width=True)
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
        selected_players = st.multiselect("Select 1–3 Anchor Players", all_players, max_selections=3)
    
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
    
                styled_df = coplayer_summary.style.format({
                    "Average Draft Position": "{:.2f}",
                    "Times Co-Drafted": "{:.0f}"
                }).background_gradient(subset=["Average Draft Position", "Times Co-Drafted"], cmap="Blues")
    
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.info("No teams drafted all selected players together.")
    
    # --- Tab 5: User Exposure Dashboard ---
    with tab5:
        st.subheader("📊 User Exposure Dashboard")
    
        # Multi-user selector
        selected_users = st.multiselect(
            "Select Users",
            sorted(df["User"].dropna().unique()),
            default=[]
        )
    
        # Filter by selected users
        if selected_users:
            exposure_df = df[df["User"].isin(selected_users)]
        else:
            exposure_df = df.copy()
    
        # Calculate exposure
        user_draft_counts = exposure_df.groupby("User")["Draft"].nunique().reset_index()
        user_draft_counts.columns = ["User", "User Drafts"]
    
        user_player_counts = exposure_df.groupby(["User", "Player"])["Draft"].nunique().reset_index()
        user_player_counts.columns = ["User", "Player", "Player Drafts"]
    
        exposure_summary = pd.merge(user_player_counts, user_draft_counts, on="User")
        exposure_summary["User Exposure %"] = (exposure_summary["Player Drafts"] / exposure_summary["User Drafts"] * 100).round(2)
    
        # Optional filters
        min_exposure = st.slider("Minimum Exposure %", 0.0, 100.0, 5.0)
        filtered_df = exposure_summary[exposure_summary["User Exposure %"] >= min_exposure]
    
        st.write(f"Filtered rows: {len(filtered_df)}")
    
        view_mode = st.radio("View mode", ["Gradient", "Editor"], horizontal=True, key="user_exposure_view_mode")
    
        if not filtered_df.empty:
            sorted_df = filtered_df.sort_values("User Exposure %", ascending=False)
            if view_mode == "Gradient":
                styled_df = sorted_df.style.format({
                    "User Exposure %": "{:.2f}",
                    "Player Drafts": "{:.0f}",
                    "User Drafts": "{:.0f}"
                }).background_gradient(subset=["User Exposure %"], cmap="Blues")
                st.dataframe(styled_df, use_container_width=True)
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
    
        # Build user-player exposure matrix
        user_player_counts = df.groupby(["User", "Player"])["Draft"].nunique().unstack(fill_value=0)
    
        # Normalize to exposure %
        user_draft_totals = df.groupby("User")["Draft"].nunique()
        exposure_matrix = user_player_counts.div(user_draft_totals, axis=0) * 100
    
        # Compute cosine similarity
        from sklearn.metrics.pairwise import cosine_similarity
        similarity_matrix = pd.DataFrame(
            cosine_similarity(exposure_matrix),
            index=exposure_matrix.index,
            columns=exposure_matrix.index
        )
    
        # Select user to compare
        selected_user = st.selectbox("Select User to Compare", sorted(similarity_matrix.index))
    
        # Filter similarity scores
        similarity_scores = similarity_matrix[selected_user].drop(selected_user).reset_index()
        similarity_scores.columns = ["User", "Similarity Score"]
        similarity_scores = similarity_scores.sort_values("Similarity Score", ascending=False)
    
        min_similarity = st.slider("Minimum Similarity Score", 0.0, 1.0, 0.5)
        filtered_scores = similarity_scores[similarity_scores["Similarity Score"] >= min_similarity]
    
        st.write(f"Users similar to `{selected_user}`: {len(filtered_scores)}")
    
        view_mode = st.radio("View mode", ["Gradient", "Editor"], horizontal=True, key="similarity_view_mode")
    
        if not filtered_scores.empty:
            if view_mode == "Gradient":
                styled_df = filtered_scores.style.format({
                    "Similarity Score": "{:.3f}"
                }).background_gradient(subset=["Similarity Score"], cmap="Greens")
                st.dataframe(styled_df, use_container_width=True)
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
    
        # --- Week-specific injury file mapping ---
        injury_file_map = {
            "Week 9": "Week9UD.csv",
            "Week 10": "week10UD.csv"
        }
    
        injury_file = injury_file_map.get(selected_week_label, "week10UD.csv")
        injury_df = pd.read_csv(f"data/{injury_file}")
        etr_df = pd.read_csv("data/ETR Projections.csv")
    
        # --- Normalize injury data ---
        injury_df["CleanStatus"] = injury_df["lineupStatus"].fillna("").str.upper().str.strip()
        injury_df["CleanName"] = (
            injury_df["firstName"].str.strip() + " " + injury_df["lastName"].str.strip()
        ).apply(clean_name)
    
        # --- Normalize ETR projections ---
        main_slate = etr_df[etr_df["Slate"].str.upper() == "MAIN"]
        main_slate["Pos"] = main_slate["Pos"].str.upper().str.strip()
        main_slate = main_slate[["Player", "Pos", "Half PPR Proj", "FD Ceiling"]].dropna()
        main_slate["CleanPlayer"] = main_slate["Player"].apply(clean_name)
    
        clean_to_original = dict(zip(main_slate["CleanPlayer"], main_slate["Player"]))
        proj_lookup = dict(zip(main_slate["CleanPlayer"], main_slate["Half PPR Proj"]))
        ceiling_lookup = dict(zip(main_slate["CleanPlayer"], main_slate["FD Ceiling"]))
    
        rankings = (
            main_slate.sort_values("Half PPR Proj", ascending=False)
            .groupby("Pos")["CleanPlayer"]
            .apply(list)
            .to_dict()
        )
    
        # --- Flex tagging function ---
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

    
        # --- Apply flex tagging ---
        df["CleanPlayer"] = df["Player"].apply(clean_name)
        df = df.groupby(["Draft", "Team"]).apply(tag_flex_players).reset_index(drop=True)
    
        # --- Select user ---
        user = st.selectbox("Select a user", df["User"].unique())
        user_drafts = df[df["User"] == user]
        user_clean_names = set(user_drafts["CleanPlayer"])
    
        # --- Manual override for QUESTIONABLE players ---
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
            toggle = st.toggle(f"{full_name} ({slot})", value=False, key=f"toggle_{clean}")
            if toggle:
                st.session_state.manual_out.add(clean)
            else:
                st.session_state.manual_out.discard(clean)
    
        manual_text = st.text_input("Manually mark a player OUT (e.g. Tyreek Hill)")
        if manual_text:
            st.session_state.manual_out.add(clean_name(manual_text))
    
        if st.session_state.manual_out:
            st.subheader("Manually Added OUT Players")
            to_remove = set()
            for name in sorted(st.session_state.manual_out):
                if not st.checkbox(f"{name}", value=True, key=f"manual_{name}"):
                    to_remove.add(name)
            st.session_state.manual_out -= to_remove
    
        # --- Build out_players dictionary scoped to drafted pool ---
        injured_df = injury_df[injury_df["CleanStatus"].isin(["OUT", "DOUBTFUL"])].copy()
        drafted_names = set(df["CleanPlayer"])
        out_players = {}
        for pos in injured_df["slotName"].dropna().unique():
            injured_at_pos = injured_df[injured_df["slotName"] == pos]
            filtered = injured_at_pos[injured_at_pos["CleanName"].apply(lambda x: is_fuzzy_match(x, drafted_names))]
            out_players[pos] = filtered["CleanName"].tolist()
    
        # --- Match mode toggle ---
        match_mode = st.radio("Replacement Match Mode", ["Fuzzy", "Exact"], horizontal=True)
    
        # --- Identify flagged drafts ---
        flagged_drafts = []
        out_names = sum(out_players.values(), []) + list(st.session_state.manual_out)
        for draft_id in user_drafts["Draft"].unique():
            full_draft = df[df["Draft"] == draft_id]
            user_picks = user_drafts[user_drafts["Draft"] == draft_id]
            user_out_picks = user_picks[user_picks["CleanPlayer"].apply(lambda x: is_fuzzy_match(x, out_names))]
            if not user_out_picks.empty:
                flagged_drafts.append((draft_id, full_draft, user_out_picks))
    
        # --- Display flagged drafts ---
        if flagged_drafts:
            st.subheader(f"Flagged Drafts for {user}")
            for draft_id, full_draft, user_out_picks in flagged_drafts:
                st.markdown(f"### Draft {draft_id}")
                st.dataframe(full_draft)
                st.markdown("**Out Players for This User:**")
                st.dataframe(user_out_picks)
       
                # --- Replacement suggestions for affected positions ---
                affected_positions = user_out_picks["Position"].unique()
                for pos in affected_positions:
                    drafted = set(full_draft[full_draft["Position"] == pos]["CleanPlayer"])
                    if match_mode == "Fuzzy":
                        available = [
                            p for p in rankings.get(pos, [])
                            if not is_fuzzy_match(p, drafted)
                        ]
                    else:
                        available = [
                            p for p in rankings.get(pos, [])
                            if p not in drafted
                        ]
    
                    st.markdown(f"**Top {pos} replacements:**")
                    for p in available[:5]:
                        name = clean_to_original.get(p, p)
                        proj = proj_lookup.get(p, "N/A")
                        ceiling = ceiling_lookup.get(p, "N/A")
                        st.write(f"{name} — Proj: {proj}, FD Ceiling: {ceiling}")
    
                # --- Swap Priority Table for This Draft ---
                st.markdown("**Swap Priority for Injured Picks in This Draft (Underdog Logic):**")

                injured_in_draft = full_draft[full_draft["CleanPlayer"].apply(lambda x: is_fuzzy_match(x, out_names))].copy()
                injured_in_draft["Round"] = injured_in_draft["Pick"].astype(int)
                injured_in_draft["PickInRound"] = injured_in_draft["Pick"].astype(int)
                injured_in_draft["Swap Priority"] = injured_in_draft.apply(
                    lambda row: (row["Round"], 13 - row["PickInRound"]), axis=1
                )
                
                injured_sorted = injured_in_draft.sort_values("Swap Priority")
                
                swap_rows = []
                used_replacements = set()
                for _, row in injured_sorted.iterrows():
                    pos = row["Position"]
                    team_id = row["Team"]
                    user_name = row["User"]
                    is_flex = row.get("IsFlex", False)
                    drafted = set(full_draft["CleanPlayer"])
                
                    # Determine eligible positions
                    eligible_positions = ["RB", "WR", "TE"] if is_flex else [pos]
                
                    # Build replacement pool
                    available = []
                    for ep in eligible_positions:
                        pool = rankings.get(ep, [])
                        for p in pool:
                            if p not in drafted and p not in used_replacements:
                                available.append(p)
                                break  # take only top available per position
                
                    replacement = available[0] if available else "None Available"
                    used_replacements.add(replacement)
                
                    swap_rows.append({
                        "Team": team_id,
                        "User": user_name,
                        "Player": row["Player"],
                        "Position": pos,
                        "Is Flex": is_flex,
                        "Round": row["Round"],
                        "Pick": row["Pick"],
                        "Swap Priority": f"{row['Round']}-{13 - row['PickInRound']}",
                        "Suggested Replacement": clean_to_original.get(replacement, replacement)
                    })
                
                swap_df = pd.DataFrame(swap_rows)
                styled_swap_df = swap_df.style.format({
                    "Pick": "{:.2f}"
                }).background_gradient(subset=["Pick"], cmap="Oranges")
                st.dataframe(styled_swap_df, use_container_width=True)

                              
    # --- Tab 8: ETR Leaderboard ---
    with tab8:
        st.subheader(f"📈 ETR Leaderboard — {selected_week_label}")
    
        # --- Load and normalize ETR projections ---
        etr_df = pd.read_csv("data/ETR Projections.csv")
        main_slate = etr_df[etr_df["Slate"].str.upper() == "MAIN"]
        main_slate = main_slate[["Player", "Half PPR Proj"]].dropna()
        main_slate["CleanPlayer"] = main_slate["Player"].apply(clean_name)
        proj_lookup = dict(zip(main_slate["CleanPlayer"], main_slate["Half PPR Proj"]))
    
        # --- Normalize draft data ---
        df["CleanPlayer"] = df["Player"].apply(clean_name)
    
        # --- Aggregate projected points and picks per team ---
        team_rows = []
        for (draft_id, team_id), group in df.groupby(["Draft", "Team"]):
            group_sorted = group.sort_values("Pick")
            clean_names = group_sorted["CleanPlayer"]
            original_names = group_sorted["Player"].tolist()
            total_proj = sum(proj_lookup.get(name, 0) for name in clean_names)
    
            row = {
                "Draft": draft_id,
                "Team": team_id,
                "User": group_sorted["User"].iloc[0],
                "Projected Points": round(total_proj, 2)
            }
    
            for i, player in enumerate(original_names):
                row[f"Round {i+1}"] = player
    
            team_rows.append(row)
    
        leaderboard_df = pd.DataFrame(team_rows)
        leaderboard_df = leaderboard_df.sort_values("Projected Points", ascending=False).reset_index(drop=True)
        leaderboard_df.index += 1
        leaderboard_df.insert(0, "Rank", leaderboard_df.index)
    
        # --- User filter (after rank is assigned) ---
        all_users = sorted(leaderboard_df["User"].dropna().unique())
        selected_user = st.selectbox("Filter by User", ["All Users"] + all_users, key="etr_user_filter")
    
        if selected_user != "All Users":
            leaderboard_df = leaderboard_df[leaderboard_df["User"] == selected_user]
    
        # --- Display leaderboard ---
        st.markdown("### 🏆 ETR Leaderboard")
        st.write(f"Teams shown: {len(leaderboard_df)}")
        styled_df = leaderboard_df.style.format({
            "Projected Points": "{:.2f}"
        }).background_gradient(subset=["Projected Points"], cmap="Greens")
        st.dataframe(styled_df, use_container_width=True)

        # --- Dashboard 1: Top 100 Team Frequency ---
        st.markdown("### 📊 Top 100 Team Frequency by User")
        
        # Get top 100 teams from full leaderboard (not filtered)
        top_100_df = leaderboard_df.sort_values("Projected Points", ascending=False).head(100)
        
        # Count top 100 appearances per user
        top_counts = top_100_df["User"].value_counts().reset_index()
        top_counts.columns = ["User", "Top 100 Teams"]
        
        # Count total teams per user
        total_counts = leaderboard_df["User"].value_counts().reset_index()
        total_counts.columns = ["User", "Total Teams"]
        
        # Merge and calculate percentage
        user_summary = pd.merge(total_counts, top_counts, on="User", how="left").fillna(0)
        user_summary["Top 100 Teams"] = user_summary["Top 100 Teams"].astype(int)
        user_summary["% in Top 100"] = (user_summary["Top 100 Teams"] / user_summary["Total Teams"] * 100).round(2)
        
        # Display
        styled_summary = user_summary.sort_values("Top 100 Teams", ascending=False).style.format({
            "% in Top 100": "{:.2f}"
        }).background_gradient(subset=["Top 100 Teams", "% in Top 100"], cmap="Blues")
        st.dataframe(styled_summary, use_container_width=True)
        
        # --- Dashboard 2: Top 30 Player Frequency + ADP Comparison ---
        st.markdown("### 📊 Top 30 Player Frequency and ADP Comparison")
    
        # Get top 30 teams from full leaderboard
        top_30_df = leaderboard_df.sort_values("Projected Points", ascending=False).head(30)
    
        # Get all players from those teams
        top_30_teams = df.merge(top_30_df[["Draft", "Team"]], on=["Draft", "Team"])
    
        # Count appearances and average ADP in top 30 teams
        top_player_counts = top_30_teams.groupby("Player")["Pick"].agg([
            ("Top 30 Appearances", "count"),
            ("Top 30 ADP", "mean")
        ]).reset_index()
    
        # Get overall ADP across all teams
        overall_adp = df.groupby("Player")["Pick"].mean().reset_index()
        overall_adp.columns = ["Player", "Overall ADP"]
    
        # Merge and calculate ADP delta
        player_summary = pd.merge(top_player_counts, overall_adp, on="Player", how="left")
        player_summary["ADP Delta"] = (player_summary["Overall ADP"] - player_summary["Top 30 ADP"]).round(2)
    
        # Display
        player_summary = player_summary.sort_values("Top 30 Appearances", ascending=False)
        styled_players = player_summary.style.format({
            "Top 30 ADP": "{:.2f}",
            "Overall ADP": "{:.2f}",
            "ADP Delta": "{:.2f}"
        }).background_gradient(subset=["Top 30 Appearances", "ADP Delta"], cmap="Purples")
        st.dataframe(styled_players, use_container_width=True)

    with tab9:
        st.subheader("📊 ETR Impact Dashboard")
    
        # Clean player names
        df["CleanPlayer"] = df["Player"].apply(clean_name)
    
        # Total drafts per group
        total_drafts = df["Draft"].nunique()
        draft_counts = df.groupby("ETR Timing")["Draft"].nunique().to_dict()
    
        # Build full player × draft grid
        all_players = df["CleanPlayer"].unique()
        all_drafts = df[["Draft", "ETR Timing"]].drop_duplicates()
        full_grid = pd.MultiIndex.from_product(
            [all_players, all_drafts["Draft"]],
            names=["CleanPlayer", "Draft"]
        ).to_frame(index=False)
        full_grid = full_grid.merge(all_drafts, on="Draft", how="left")
    
        # Merge actual picks
        merged = full_grid.merge(df[["Draft", "CleanPlayer", "Pick"]], on=["Draft", "CleanPlayer"], how="left")
        merged["Pick"] = merged["Pick"].fillna(72)
    
        # Group by player and timing
        grouped = merged.groupby(["CleanPlayer", "ETR Timing"]).agg(
            ADP=("Pick", "mean"),
            Drafted=("Pick", lambda x: (x < 72).sum())
        ).reset_index()
        grouped["% Drafted"] = grouped.apply(
            lambda row: row["Drafted"] / draft_counts.get(row["ETR Timing"], 1), axis=1
        )
    
        # Group across all drafts
        all_grouped = merged.groupby("CleanPlayer").agg(
            ADP_All=("Pick", "mean"),
            Drafted_All=("Pick", lambda x: (x < 72).sum())
        ).reset_index()
        all_grouped["% Drafted_All"] = all_grouped["Drafted_All"] / total_drafts
    
        # Pivot Pre/Post
        pivot = grouped.pivot(index="CleanPlayer", columns="ETR Timing", values=["ADP", "% Drafted"])
        pivot.columns = ["ADP_Pre", "ADP_Post", "Pct_Pre", "Pct_Post"]
        pivot = pivot.reset_index()
    
        # Merge with overall stats
        summary = pivot.merge(all_grouped, on="CleanPlayer", how="left")
    
        # Calculate differences
        summary["ADP_Diff"] = summary["ADP_Post"] - summary["ADP_Pre"]
        summary["Pct_Diff"] = summary["Pct_Post"] - summary["Pct_Pre"]
    
        # Optional: add original player name
        name_map = df[["CleanPlayer", "Player"]].drop_duplicates()
        summary = summary.merge(name_map, on="CleanPlayer", how="left")
    
        # Reorder columns
        summary = summary[[
            "Player", "ADP_Pre", "ADP_Post", "ADP_All", "ADP_Diff",
            "Pct_Pre", "Pct_Post", "% Drafted_All", "Pct_Diff"
        ]].sort_values("ADP_Diff", ascending=False)
    
        # Display
        st.write(f"Players compared: {len(summary)}")
        styled = summary.style.format({
            "ADP_Pre": "{:.2f}", "ADP_Post": "{:.2f}", "ADP_All": "{:.2f}", "ADP_Diff": "{:.2f}",
            "Pct_Pre": "{:.2%}", "Pct_Post": "{:.2%}", "% Drafted_All": "{:.2%}", "Pct_Diff": "{:.2%}"
        }).background_gradient(subset=["ADP_Diff", "Pct_Diff"], cmap="coolwarm")
        st.dataframe(styled, use_container_width=True)

elif auth_status is False:
    st.error("Username or password is incorrect ❌")

elif auth_status is None:
    st.warning("Please enter your credentials 🔐")
