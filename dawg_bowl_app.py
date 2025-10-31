import streamlit as st
import streamlit_authenticator as stauth
import yaml

st.set_page_config(layout="wide")

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

config = yaml.safe_load(config_yaml)
st.write(config)  # Optional debug print

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

name, auth_status, username = authenticator.login("Login", "main")

if auth_status:
    st.success(f"Welcome {name} 👋")
    
    import pandas as pd
    from utils.draft_helpers import calculate_adp


    # --- Load Draft Data First ---
    df = pd.read_csv("data/week9_drafts.csv", sep=None, engine="python")
    
    # --- Shared Filters (now safe to use df) ---
    all_positions = sorted(df["Position"].dropna().unique())
    shared_positions = st.multiselect("Filter by Position (shared)", all_positions, default=all_positions, key="shared_position_filter")
    
    adp_min, adp_max = df["Pick"].min(), df["Pick"].max()
    shared_adp_range = st.slider("Filter by ADP Range (shared)", float(adp_min), float(adp_max), (float(adp_min), float(adp_max)), key="shared_adp_filter")
    
    if st.button("🔄 Reset Filters"):
        st.experimental_rerun()
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Draft Viewer",
        "📋 Player Dashboard",
        "🔍 Combo Finder",
        "🤝 Co-Drafted Dashboard",
        "📊 User Exposure Dashboard",
        "🧠 User Similarity Dashboard"  # 👈 Add this sixth label
    ])
    
    # --- Tab 1: Draft Viewer ---
    with tab1:
        st.subheader("📋 Draft Viewer")
    
        # Select a draft number
        all_drafts = sorted(df["Draft"].unique())
        selected_draft = st.selectbox("Select Draft Number", all_drafts)
    
        # Filter to selected draft
        draft_df = df[df["Draft"] == selected_draft]
    
        # Group by Team and show players + user
        team_groups = draft_df.groupby("Team")
        for team_num, group in team_groups:
            st.markdown(f"### 🏈 Team {team_num} — User: `{group['User'].iloc[0]}`")
    
            team_df = group[["Player", "Position", "NFL_Team", "Pick"]].sort_values("Pick")
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
    
        # Filter base dataframe using shared filters
        combo_df = df[
            (df["Position"].isin(shared_positions)) &
            (df["Pick"] >= shared_adp_range[0]) &
            (df["Pick"] <= shared_adp_range[1])
        ]
    
        # Build combos per fantasy team (Draft + Team)
        combo_pairs = []
        for (draft_id, team_id), group in combo_df.groupby(["Draft", "Team"]):
            player_team_map = group.set_index("Player")["NFL_Team"].to_dict()
            players = sorted(player_team_map.keys())
            for i in range(len(players)):
                for j in range(i + 1, len(players)):
                    combo_pairs.append({
                        "Player A": players[i],
                        "Player B": players[j],
                        "Team A": player_team_map[players[i]],
                        "Team B": player_team_map[players[j]]
                    })
    
        combo_df = pd.DataFrame(combo_pairs)
        combo_df["Is_Teammate"] = combo_df["Team A"] == combo_df["Team B"]
    
        combo_summary = combo_df.groupby(["Player A", "Player B", "Is_Teammate"]).size().reset_index(name="Times Drafted Together")
        combo_summary["Exposure %"] = (combo_summary["Times Drafted Together"] / df["Draft"].nunique() * 100).round(2)
    
        # Filter by minimum frequency
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
                    "Exposure %": "{:.2f}"
                }).background_gradient(subset=["Times Drafted Together", "Exposure %"], cmap="Blues")
                st.dataframe(styled, use_container_width=True)
            else:
                st.data_editor(
                    all_combo_df,
                    use_container_width=True,
                    height=900,
                    column_config={
                        "Times Drafted Together": st.column_config.NumberColumn(format="%d"),
                        "Exposure %": st.column_config.NumberColumn(format="%.2f")
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
                    "Exposure %": "{:.2f}"
                }).background_gradient(subset=["Times Drafted Together", "Exposure %"], cmap="Oranges")
                st.dataframe(styled, use_container_width=True)
            else:
                st.data_editor(
                    non_teammates_df,
                    use_container_width=True,
                    height=900,
                    column_config={
                        "Times Drafted Together": st.column_config.NumberColumn(format="%d"),
                        "Exposure %": st.column_config.NumberColumn(format="%.2f")
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
    
elif auth_status is False:
    st.error("Username or password is incorrect ❌")

elif auth_status is None:
    st.warning("Please enter your credentials 🔐")
