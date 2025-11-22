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

    # --- Week Defaults ---
    DEFAULT_WEEK = 12
    DATA_FILES = {
        12: {
            "ud": "data/week12UD.csv",
            "drafts": "data/week12_drafts.csv"
        },
        # Add later weeks here if needed
        # 13: {"ud": "data/week13UD.csv", "drafts": "data/week13_drafts.csv"},
    }
    
    def load_week_data(week: int = DEFAULT_WEEK):
        files = DATA_FILES.get(week)
        if not files:
            raise ValueError(f"No data files configured for week {week}")
        ud_df = pd.read_csv(files["ud"])
        df = pd.read_csv(files["drafts"])   # <-- keep drafts as df
        return ud_df, df
    
    # --- Load Week 12 by default ---
    ud_df, df = load_week_data()
    
    # Define a reusable label for downstream tabs
    selected_week_label = f"Week {DEFAULT_WEEK}"
    
    # Use it in your title
    st.title(f"Dawg Bowl Contest Dashboard — {selected_week_label}")

    
    st.title(f"Dawg Bowl Contest Dashboard — Week {DEFAULT_WEEK}")


    # --- Normalize draft data ---
    if "Team" in df.columns and "NFL_Team" not in df.columns:
        df = df.rename(columns={"Team": "NFL_Team"})
    df["CleanPlayer"] = df["Player"].apply(clean_name)


    # --- Shared Filters ---
    all_positions = sorted(df["Position"].dropna().unique())
    shared_positions = st.multiselect(
        "Filter by Position (shared)",
        all_positions,
        default=all_positions,
        key="shared_position_filter"
    )
    
    adp_min, adp_max = df["Pick"].min(), df["Pick"].max()
    shared_adp_range = st.slider(
        "Filter by ADP Range (shared)",
        float(adp_min),
        float(adp_max),
        (float(adp_min), float(adp_max)),
        key="shared_adp_filter"
    )


    if st.button("🔄 Reset Filters"):
        st.experimental_rerun()

    # --- Tab Layout ---
    selected_tab = st.sidebar.radio("📂 Select a View", [
        "📋 Draft Viewer",
        "📋 Player Dashboard",
        "🔍 Combo Finder",
        "🤝 Co-Drafted Dashboard",
        "📊 User Exposure Dashboard",
        "🧠 User Similarity Dashboard",
        "🩹 Injury Swap",
        "📈 ETR Leaderboard",
        "📊 ETR Impact Dashboard",
        "📉 ADP Change Tracker",
        "📋 User Draft Teams"
    ])

    # --- Tab 1: Draft Viewer ---
    if selected_tab == "📋 Draft Viewer":
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
    elif selected_tab == "📋 Player Dashboard":
        st.subheader("📋 Player Dashboard")
    
        # Base ADP across all drafts
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
    
        # Load UD IDs for current week (use DEFAULT_WEEK)
        try:
            ud_df = pd.read_csv(
                f"data/week{DEFAULT_WEEK}UD.csv",
                usecols=[0, 1, 2],
                names=["id", "First", "Last"],
                header=0
            )
            ud_df["FullName"] = (ud_df["First"].str.strip() + " " + ud_df["Last"].str.strip()).str.strip()
            ud_df["CleanPlayer"] = ud_df["FullName"].apply(clean_name)
            dashboard_df["CleanPlayer"] = dashboard_df["Player"].apply(clean_name)
            dashboard_df = dashboard_df.merge(ud_df[["CleanPlayer", "id"]], on="CleanPlayer", how="left")
        except FileNotFoundError:
            st.warning(f"UD ID file for Week {DEFAULT_WEEK} not found. Player IDs will be missing.")
            dashboard_df["id"] = None
        except Exception as e:
            st.warning(f"UD ID file for Week {DEFAULT_WEEK} could not be parsed: {e}")
            dashboard_df["id"] = None
    
        # --- NEW: Post-ETR ADP (numeric) only if Post-ETR rows exist ---
        show_post_etr_adp = False
        if "ETR Timing" in df.columns:
            df["ETR Timing"] = df["ETR Timing"].astype(str).str.strip()
            post_etr_df = df[df["ETR Timing"].str.upper() == "POST-ETR"].copy()
            post_etr_draft_ids = sorted(post_etr_df["Draft"].unique())
            if len(post_etr_draft_ids) > 0:
                show_post_etr_adp = True
    
                # Build full grid of Player x Post-ETR Draft, fill missing with 72, then mean
                all_players = pd.DataFrame(df["Player"].unique(), columns=["Player"])
                grid = pd.MultiIndex.from_product(
                    [all_players["Player"], post_etr_draft_ids],
                    names=["Player", "Draft"]
                ).to_frame(index=False)
    
                post_etr_picks = post_etr_df[["Player", "Draft", "Pick"]].copy()
                post_etr_grid = grid.merge(post_etr_picks, on=["Player", "Draft"], how="left")
                post_etr_grid["Pick"] = post_etr_grid["Pick"].fillna(72)
    
                post_etr_adp = (
                    post_etr_grid.groupby("Player")["Pick"].mean().reset_index()
                    .rename(columns={"Pick": "Post-ETR ADP"})
                )
                post_etr_adp["Post-ETR ADP"] = post_etr_adp["Post-ETR ADP"].round(2)
    
                dashboard_df = dashboard_df.merge(post_etr_adp, on="Player", how="left")
    
        # Filters
        positions = sorted(dashboard_df["Position"].dropna().unique())
        selected_positions = st.multiselect("Filter by Position", positions, default=positions, key="tab2_position")
    
        adp_min, adp_max = dashboard_df["Average Draft Position"].min(), dashboard_df["Average Draft Position"].max()
        adp_range = st.slider(
            "Filter by ADP Range",
            float(adp_min), float(adp_max),
            (float(adp_min), float(adp_max)),
            key="tab2_adp"
        )
    
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
    
        # Display columns (insert Post-ETR ADP right after ADP if present)
        display_cols = [
            "id", "Player", "Position", "NFL_Team", "Average Draft Position"
        ]
        if show_post_etr_adp and "Post-ETR ADP" in filtered_df.columns:
            display_cols.append("Post-ETR ADP")
        display_cols += [
            "Earliest Pick", "Latest Pick", "Exposure", "Stack Rate"
        ]
        if "User Exposure %" in filtered_df.columns:
            display_cols.insert(display_cols.index("Stack Rate"), "User Exposure %")
    
        filtered_df = filtered_df[display_cols]
        display_cols_for_table = [col for col in display_cols if col != "id"]
    
        st.write(f"Filtered rows: {len(filtered_df)}")
    
        if not filtered_df.empty:
            sorted_df = filtered_df.sort_values("Average Draft Position")
    
            gradient_cols = ["Average Draft Position", "Exposure", "Stack Rate"]
            if show_post_etr_adp and "Post-ETR ADP" in sorted_df.columns:
                gradient_cols.append("Post-ETR ADP")
            if "User Exposure %" in sorted_df.columns:
                gradient_cols.append("User Exposure %")
    
            styled_df = sorted_df[display_cols_for_table].style.background_gradient(
                subset=gradient_cols, cmap="Blues"
            ).format({
                "Average Draft Position": "{:.2f}",
                "Exposure": "{:.2f}",
                "Stack Rate": "{:.2f}",
                "Post-ETR ADP": "{:.2f}" if ("Post-ETR ADP" in sorted_df.columns) else None,
                "User Exposure %": "{:.2f}" if ("User Exposure %" in sorted_df.columns) else None
            })
    
            st.dataframe(styled_df, use_container_width=True)
    
            csv_bytes = sorted_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download CSV (with id)",
                data=csv_bytes,
                file_name=f"Week{DEFAULT_WEEK}_PlayerDashboard.csv",
                mime="text/csv",
                key="tab2_download"
            )
        else:
            st.warning("No players match the current filters.")



    
    # --- Tab 3: Combo Finder ---
    elif selected_tab == "🔍 Combo Finder":
        st.subheader("🔍 Combo Finder")

        all_users = sorted(df["User"].dropna().unique())
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
                styled_all = all_combo_df.style.background_gradient(
                    subset=["Times Drafted Together", "Exposure %", "ADP A", "ADP B"],
                    cmap="Blues"
                ).format({
                    "Times Drafted Together": "{:.0f}",
                    "Exposure %": "{:.2f}",
                    "ADP A": "{:.2f}",
                    "ADP B": "{:.2f}"
                })
                st.dataframe(styled_all, use_container_width=True)
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
                styled_non = non_teammates_df.style.background_gradient(
                    subset=["Times Drafted Together", "Exposure %", "ADP A", "ADP B"],
                    cmap="Oranges"
                ).format({
                    "Times Drafted Together": "{:.0f}",
                    "Exposure %": "{:.2f}",
                    "ADP A": "{:.2f}",
                    "ADP B": "{:.2f}"
                })
                st.dataframe(styled_non, use_container_width=True)
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
    elif selected_tab == "🤝 Co-Drafted Dashboard":
        st.subheader("🤝 Co-Drafted Dashboard")
    
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
    
                styled_df = coplayer_summary.style.background_gradient(
                    subset=["Times Co-Drafted", "Average Draft Position"],
                    cmap="Blues"
                ).format({
                    "Average Draft Position": "{:.2f}",
                    "Times Co-Drafted": "{:.0f}"
                })
    
                st.dataframe(styled_df, use_container_width=True)
    
                # --- Matching Team Rosters ---
                st.markdown("### 🧠 Matching Teams with Anchor Combo")
    
                for _, row in matching_teams.iterrows():
                    draft_id = row["Draft"]
                    team_players = row["Player"]
                    team_df = df[(df["Draft"] == draft_id) & (df["Player"].isin(team_players))].copy()
                    team_df = team_df.sort_values("Pick")
    
                    used_players = set()
    
                    def get_first(pos):
                        for _, r in team_df.iterrows():
                            if r["Position"] == pos and r["Player"] not in used_players:
                                used_players.add(r["Player"])
                                return f"{r['Player']} (Pick {r['Pick']})"
                        return ""
    
                    def get_next_flex():
                        for _, r in team_df.iterrows():
                            if r["Position"] in ["RB", "WR", "TE"] and r["Player"] not in used_players:
                                used_players.add(r["Player"])
                                return f"{r['Player']} (Pick {r['Pick']})"
                        return ""
    
                    qb = get_first("QB")
                    rb = get_first("RB")
                    wr1 = get_first("WR")
                    wr2 = get_first("WR")
                    te = get_first("TE")
                    flex = get_next_flex()
    
                    user = team_df["User"].iloc[0]
                    team_id = team_df["Team"].iloc[0]
    
                    st.markdown(f"#### 🏈 Draft {draft_id} — Team {team_id} — User: `{user}`")
                    st.table(pd.DataFrame([{
                        "QB": qb,
                        "RB": rb,
                        "WR1": wr1,
                        "WR2": wr2,
                        "TE": te,
                        "Flex": flex
                    }]))
            else:
                st.info("No teams drafted all selected players together.")


    
    # --- Tab 5: User Exposure Dashboard ---
    elif selected_tab == "📊 User Exposure Dashboard":
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
        exposure_summary["User Exposure %"] = (
            exposure_summary["Player Drafts"] / exposure_summary["User Drafts"] * 100
        ).round(2)
    
        # --- NEW: Minimum drafts filter ---
        min_drafts = st.slider(
            "Minimum Number of Drafts",
            0,
            int(user_draft_counts["User Drafts"].max()),
            1,
            key="tab5_min_drafts"
        )
        exposure_summary = exposure_summary[exposure_summary["User Drafts"] >= min_drafts]
    
        # Optional filters
        min_exposure = st.slider("Minimum Exposure %", 0.0, 100.0, 5.0, key="tab5_min_exposure")
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
    
        # --- 🎯 Pick Frequency by User ---
        st.markdown("### 🎯 Pick Frequency by User")
    
        pick_number = st.slider("Select Pick Number", 1, 12, 1, key="tab5_pick_number")
    
        pick_counts = df[df["Pick"] == pick_number].groupby("User")["Draft"].nunique().reset_index()
        pick_counts.columns = ["User", "Pick Count"]
    
        total_counts = df.groupby("User")["Draft"].nunique().reset_index()
        total_counts.columns = ["User", "Total Drafts"]
    
        pick_summary = pd.merge(total_counts, pick_counts, on="User", how="left").fillna(0)
        pick_summary["Pick Count"] = pick_summary["Pick Count"].astype(int)
        pick_summary["Pick %"] = (pick_summary["Pick Count"] / pick_summary["Total Drafts"] * 100).round(2)
    
        expected_pct = 100 / 12
        pick_summary["Over Expected %"] = (pick_summary["Pick %"] - expected_pct).round(2)
    
        # Apply min drafts filter here too
        pick_summary = pick_summary[pick_summary["Total Drafts"] >= min_drafts]
        pick_summary = pick_summary.sort_values("Pick Count", ascending=False)
    
        styled_pick_summary = pick_summary.style.format({
            "Pick %": "{:.2f}",
            "Over Expected %": "{:.2f}"
        }).background_gradient(subset=["Pick Count", "Pick %", "Over Expected %"], cmap="Oranges")
    
        st.dataframe(styled_pick_summary, use_container_width=True)

  
    # --- Tab 6: User Similarity Dashboard ---
    elif selected_tab == "🧠 User Similarity Dashboard":
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
                styled_df = filtered_scores.style.background_gradient(
                    subset=["Similarity Score"], cmap="Blues"
                ).format({
                    "Similarity Score": "{:.3f}"
                })
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

        
    # --- Tab 7: Injury Swap ---
    elif selected_tab == "🩹 Injury Swap":
        st.header(f"🩹 Injury Swap Tool — Week {DEFAULT_WEEK}")
    
        # --- Correlation Boost Slider ---
        correlation_boost = st.slider(
            "Correlation Boost",
            0.0, 2.0, 1.0, 0.1,
            key="injury_swap_boost"
        )
    
        # --- Week-specific injury file mapping ---
        injury_file_map = {
            "Week 9": "Week9UD.csv",
            "Week 10": "week10UD.csv",
            "Week 11": "week11UD.csv",
            "Week 12": "week12UD.csv"
        }
        injury_file = injury_file_map.get(selected_week_label, f"week{DEFAULT_WEEK}UD.csv")
        injury_df = pd.read_csv(f"data/{injury_file}")
        etr_df = pd.read_csv("data/ETR Projections.csv", sep=",")
    
        # --- Normalize injury data ---
        injury_df["CleanStatus"] = injury_df["lineupStatus"].fillna("").str.upper().str.strip()
        injury_df["CleanName"] = (
            injury_df["firstName"].str.strip() + " " + injury_df["lastName"].str.strip()
        ).apply(clean_name)
    
        # --- Normalize ETR projections ---
        main_slate = etr_df[etr_df["Slate"].str.upper() == "MAIN"]
        main_slate["Pos"] = main_slate["Pos"].str.upper().str.strip()
        main_slate["Team"] = main_slate["Team"].str.upper().str.strip()
        main_slate = main_slate[["Player", "Pos", "Team", "Half PPR Proj", "FD Ceiling"]].dropna()
        main_slate["CleanPlayer"] = main_slate["Player"].apply(clean_name)
    
        clean_to_original = dict(zip(main_slate["CleanPlayer"], main_slate["Player"]))
        proj_lookup = dict(zip(main_slate["CleanPlayer"], main_slate["Half PPR Proj"]))
        ceiling_lookup = dict(zip(main_slate["CleanPlayer"], main_slate["FD Ceiling"]))
        team_lookup = dict(zip(main_slate["CleanPlayer"], main_slate["Team"]))
    
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
    
                # --- Replacement suggestions with stack-aware boost ---
                affected_positions = user_out_picks["Position"].unique()
                drafted_qbs = full_draft[full_draft["Position"] == "QB"]["CleanPlayer"].map(team_lookup).dropna().unique()
                drafted_passcatchers = full_draft[full_draft["Position"].isin(["WR", "TE"])]["CleanPlayer"].map(team_lookup).dropna().unique()
    
                for pos in affected_positions:
                    drafted = set(full_draft[full_draft["Position"] == pos]["CleanPlayer"])
                    scored_candidates = []
                    for p in rankings.get(pos, []):
                        if p in drafted:
                            continue
                        team = team_lookup.get(p, None)
                        boost = 0
                        if pos in ["WR", "TE"] and team in drafted_qbs:
                            boost += correlation_boost
                        elif pos == "QB" and team in drafted_passcatchers:
                            boost += correlation_boost
                        base_proj = proj_lookup.get(p, 0)
                        scored_candidates.append((p, base_proj + boost))
    
                    scored_candidates.sort(key=lambda x: x[1], reverse=True)
                    available = [p for p, _ in scored_candidates]
    
                    st.markdown(f"**Top {pos} replacements:**")
                    for p in available[:5]:
                        name = clean_to_original.get(p, p)
                        proj = proj_lookup.get(p, "N/A")
                        ceiling = ceiling_lookup.get(p, "N/A")
                        st.write(f"{name} — Proj: {proj}, FD Ceiling: {ceiling}")
    
                # --- Swap Priority Table ---
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
                    eligible_positions = ["RB", "WR", "TE"] if is_flex else [pos]
                    scored_candidates = []
    
                    drafted_qbs = full_draft[full_draft["Position"] == "QB"]["CleanPlayer"].map(team_lookup).dropna().unique()
                    drafted_passcatchers = full_draft[full_draft["Position"].isin(["WR", "TE"])]["CleanPlayer"].map(team_lookup).dropna().unique()
    
                    for ep in eligible_positions:
                        for p in rankings.get(ep, []):
                            if p in drafted or p in used_replacements:
                                continue
                            team = team_lookup.get(p, None)
                            boost = 0
                            if ep in ["WR", "TE"] and team in drafted_qbs:
                                boost += correlation_boost
                            elif ep == "QB" and team in drafted_passcatchers:
                                boost += correlation_boost
                            base_proj = proj_lookup.get(p, 0)
                            scored_candidates.append((p, base_proj + boost))
    
                    scored_candidates.sort(key=lambda x: x[1], reverse=True)
                    replacement = scored_candidates[0][0] if scored_candidates else "None Available"
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

            # --- Adjustable Global Swap Mapping ---
            st.markdown("**Adjust Global Swap Choices:**")
            
            # ✅ Ensure CleanPlayer column exists in injury_df
            if "CleanPlayer" not in injury_df.columns:
                injury_df["CleanPlayer"] = (
                    injury_df["firstName"].str.strip() + " " + injury_df["lastName"].str.strip()
                ).apply(clean_name)
            
            global_swap_map = {}
            
            # Loop through injured players
            for injured_player in injury_df["CleanPlayer"].unique():
                # Get suggested replacements for this specific injured player
                player_suggestions = swap_df.loc[
                    swap_df["Player"].apply(clean_name) == injured_player, "Suggested Replacement"
                ].dropna().unique().tolist()
            
                # Fallback: if no specific suggestions, show the whole pool
                if not player_suggestions:
                    player_suggestions = swap_df["Suggested Replacement"].dropna().unique().tolist()
            
                chosen = st.selectbox(
                    f"Replacement for {clean_to_original.get(injured_player, injured_player)}",
                    options=player_suggestions,
                    index=0,
                    key=f"global_swap_{injured_player}"
                )
                global_swap_map[injured_player] = chosen
            
            # --- Exposure Impact After Global Swaps (Step 2) ---
            st.header("📊 Exposure Impact After Global Swaps")
            
            all_after_players = []
            for draft_id, full_draft, user_out_picks in flagged_drafts:
                # Apply global swap overrides to each draft roster
                after_players = full_draft["CleanPlayer"].replace(global_swap_map)
                all_after_players.extend(after_players.tolist())
            
            # Aggregate exposures across all drafts
            after_counts = pd.Series(all_after_players).value_counts()
            before_counts = df["CleanPlayer"].value_counts()
            
            exposure_df = pd.DataFrame({
                "Player": before_counts.index,
                "Before": before_counts.values,
                "After": after_counts.reindex(before_counts.index).fillna(0).values
            })
            exposure_df["Delta"] = exposure_df["After"] - exposure_df["Before"]
            
            # Optional: add gradient formatting for clarity
            styled_exposure = exposure_df.style.background_gradient(
                subset=["Delta"], cmap="RdYlGn"
            ).format({"Before":"{:.0f}", "After":"{:.0f}", "Delta":"{:+.0f}"})
            
            st.dataframe(styled_exposure, use_container_width=True)

            # --- Global Swap List from Suggested Replacements ---
            st.header("🩹 Global Swap List — Suggested Replacements (Extended)")
            
            all_suggested = []
            for draft_id, full_draft, user_out_picks in flagged_drafts:
                drafted_qbs = full_draft[full_draft["Position"] == "QB"]["CleanPlayer"].map(team_lookup).dropna().unique()
                drafted_passcatchers = full_draft[full_draft["Position"].isin(["WR", "TE"])]["CleanPlayer"].map(team_lookup).dropna().unique()
                drafted = set(full_draft["CleanPlayer"])
                used_replacements = set()
            
                injured_sorted = user_out_picks.copy()
                injured_sorted["Round"] = injured_sorted["Pick"].astype(int)
                injured_sorted["PickInRound"] = injured_sorted["Pick"].astype(int)
                injured_sorted["Swap Priority"] = injured_sorted.apply(
                    lambda row: (row["Round"], 13 - row["PickInRound"]), axis=1
                )
                injured_sorted = injured_sorted.sort_values("Swap Priority")
            
                for _, row in injured_sorted.iterrows():
                    pos = row["Position"]
                    is_flex = row.get("IsFlex", False)
                    eligible_positions = ["RB", "WR", "TE"] if is_flex else [pos]
                    scored_candidates = []
            
                    for ep in eligible_positions:
                        for p in rankings.get(ep, []):
                            if p in drafted or p in used_replacements:
                                continue
                            team = team_lookup.get(p, None)
                            boost = 0
                            if ep in ["WR", "TE"] and team in drafted_qbs:
                                boost += correlation_boost
                            elif ep == "QB" and team in drafted_passcatchers:
                                boost += correlation_boost
                            base_proj = proj_lookup.get(p, 0)
                            scored_candidates.append((p, base_proj + boost))
            
                    scored_candidates.sort(key=lambda x: x[1], reverse=True)
            
                    # Expanded: capture multiple candidates, not just the top one
                    for cand, _ in scored_candidates[:5]:
                        if cand not in used_replacements:
                            all_suggested.append(cand)
                            used_replacements.add(cand)
            
            # --- Build DataFrame of unique suggestions ---
            unique_suggestions = list(set(all_suggested))
            swap_rows = []
            for p in unique_suggestions:
                original = clean_to_original.get(p, p)
                pos = main_slate.loc[main_slate["CleanPlayer"] == p, "Pos"].values[0]
                team = team_lookup.get(p, "Unknown")
                proj = proj_lookup.get(p, 0)
                ceiling = ceiling_lookup.get(p, 0)
            
                swap_rows.append({
                    "Player": original,
                    "Position": pos,
                    "Team": team,
                    "Projection": round(proj, 2),
                    "Ceiling": round(ceiling, 2)
                })
            
            swap_df = pd.DataFrame(swap_rows)
            swap_df = swap_df.sort_values("Projection", ascending=False).reset_index(drop=True)
            
            # --- Style and display table ---
            styled_swap_df = swap_df.style.format({
                "Projection": "{:.2f}",
                "Ceiling": "{:.2f}"
            }).background_gradient(subset=["Projection"], cmap="Greens")
            
            st.dataframe(styled_swap_df, use_container_width=True)
            
            # --- Export CSV aligned with table order ---
            injury_df["CleanPlayer"] = (
                injury_df["firstName"].str.strip() + " " + injury_df["lastName"].str.strip()
            ).apply(clean_name)
            injury_id_lookup = dict(zip(injury_df["CleanPlayer"], injury_df["id"]))
            
            export_df = swap_df.copy()
            export_df["id"] = export_df["Player"].apply(lambda p: injury_id_lookup.get(clean_name(p), ""))
            
            csv_data = export_df[["id", "Player"]].to_csv(index=False).encode("utf-8")
            
            st.download_button(
                label="📥 Download Global Swap List (CSV)",
                data=csv_data,
                file_name="global_swap_list.csv",
                mime="text/csv"
            )


            # --- Exposure Comparison (Pre vs Post Swaps for Selected User) ---
            st.markdown("### 📊 Exposure Comparison (Selected User Only)")
            selected_user = user
    
            all_swaps = []
            for draft_id, full_draft, user_out_picks in flagged_drafts:
                injured_in_draft = full_draft[full_draft["CleanPlayer"].apply(lambda x: is_fuzzy_match(x, out_names))].copy()
                injured_in_draft["Round"] = injured_in_draft["Pick"].astype(int)
                injured_in_draft["PickInRound"] = injured_in_draft["Pick"].astype(int)
                injured_in_draft["Swap Priority"] = injured_in_draft.apply(
                    lambda row: (row["Round"], 13 - row["PickInRound"]), axis=1
                )
                injured_sorted = injured_in_draft.sort_values("Swap Priority")
    
                used_replacements = set()
                drafted_qbs = full_draft[full_draft["Position"] == "QB"]["CleanPlayer"].map(team_lookup).dropna().unique()
                drafted_passcatchers = full_draft[full_draft["Position"].isin(["WR", "TE"])]["CleanPlayer"].map(team_lookup).dropna().unique()
                drafted_clean = set(full_draft["CleanPlayer"])
    
                for _, row in injured_sorted.iterrows():
                    pos = row["Position"]
                    is_flex = row.get("IsFlex", False)
                    eligible_positions = ["RB", "WR", "TE"] if is_flex else [pos]
                    scored_candidates = []
                    for ep in eligible_positions:
                        for p in rankings.get(ep, []):
                            if p in drafted_clean or p in used_replacements:
                                continue
                            team = team_lookup.get(p, None)
                            boost = 0
                            if ep in ["WR", "TE"] and team in drafted_qbs:
                                boost += correlation_boost
                            elif ep == "QB" and team in drafted_passcatchers:
                                boost += correlation_boost
                            base_proj = proj_lookup.get(p, 0)
                            scored_candidates.append((p, base_proj + boost))
                    scored_candidates.sort(key=lambda x: x[1], reverse=True)
                    replacement_clean = scored_candidates[0][0] if scored_candidates else None
                    if replacement_clean:
                        used_replacements.add(replacement_clean)
                    all_swaps.append({
                        "Draft": draft_id,
                        "Out_Player": row["Player"],
                        "Out_Clean": row["CleanPlayer"],
                        "Position": pos,
                        "IsFlex": is_flex,
                        "Suggested_Replacement_Clean": replacement_clean,
                        "Suggested_Replacement": clean_to_original.get(replacement_clean, replacement_clean) if replacement_clean else None
                    })
    
            swaps_df = pd.DataFrame(all_swaps)
            user_drafts = df[df["User"] == selected_user].copy()
            total_user_drafts = user_drafts["Draft"].nunique()
    
            # Pre-swap exposure
            pre_exposure = (
                user_drafts.groupby("Player")["Draft"].nunique().reset_index()
                .rename(columns={"Draft": "Pre_Drafts"})
            )
            pre_exposure["Pre-Swap Exposure %"] = (
                pre_exposure["Pre_Drafts"] / total_user_drafts * 100
            ).round(2)
    
            # Build replacement map
            valid_swaps = swaps_df.dropna(subset=["Suggested_Replacement_Clean"]).copy()
            replacement_map = {
                (int(row["Draft"]), row["Out_Clean"]): row["Suggested_Replacement_Clean"]
                for _, row in valid_swaps.iterrows()
            }
    
            # Apply replacements to user_drafts copy
            post_df = user_drafts.copy()
            post_df["CleanPlayer"] = post_df["Player"].apply(clean_name)
    
            def apply_swap(row):
                key = (int(row["Draft"]), row["CleanPlayer"])
                if key in replacement_map:
                    new_clean = replacement_map[key]
                    new_name = clean_to_original.get(new_clean, row["Player"])
                    return pd.Series({"Player": new_name, "CleanPlayer": new_clean})
                else:
                    return pd.Series({"Player": row["Player"], "CleanPlayer": row["CleanPlayer"]})
    
            post_df[["Player", "CleanPlayer"]] = post_df.apply(apply_swap, axis=1)
    
            # Post-swap exposure
            post_exposure = (
                post_df.groupby("Player")["Draft"].nunique().reset_index()
                .rename(columns={"Draft": "Post_Drafts"})
            )
            post_exposure["Post-Swap Exposure %"] = (
                post_exposure["Post_Drafts"] / total_user_drafts * 100
            ).round(2)
    
            # Combine and show delta
            exposure_compare = (
                pre_exposure[["Player", "Pre-Swap Exposure %"]]
                .merge(post_exposure[["Player", "Post-Swap Exposure %"]], on="Player", how="outer")
                .fillna(0)
            )
            exposure_compare["Exposure Δ"] = (
                exposure_compare["Post-Swap Exposure %"] - exposure_compare["Pre-Swap Exposure %"]
            ).round(2)
    
            # Sort by delta
            exposure_compare = exposure_compare.sort_values(
                ["Exposure Δ", "Post-Swap Exposure %"], ascending=[False, False]
            )
    
            styled_exposure = exposure_compare.style.background_gradient(
                subset=["Pre-Swap Exposure %", "Post-Swap Exposure %"], cmap="Blues"
            ).background_gradient(
                subset=["Exposure Δ"], cmap="coolwarm"
            ).format({
                "Pre-Swap Exposure %": "{:.2f}",
                "Post-Swap Exposure %": "{:.2f}",
                "Exposure Δ": "{:.2f}"
            })
    
            st.dataframe(styled_exposure, use_container_width=True)
        else:
            st.info("No injury swaps available for the current selection.")

                             
    
    # --- Tab8: ETR Leaderboard ---
    elif selected_tab == "📈 ETR Leaderboard":
        st.subheader(f"📈 ETR Leaderboard — {selected_week_label}")
    
        # --- Load and normalize ETR projections ---
        try:
            etr_df = pd.read_csv("data/ETR Projections.csv")  # <-- fixed separator
            etr_df["Slate"] = etr_df["Slate"].astype(str).str.strip().str.upper()
            etr_df["CleanPlayer"] = etr_df["Player"].apply(clean_name)
            main_slate = etr_df[etr_df["Slate"] == "MAIN"]
            if main_slate.empty:
                st.warning("No MAIN slate rows found in ETR projections.")
            main_slate = main_slate[["Player", "Half PPR Proj", "CleanPlayer"]].dropna()
            proj_lookup = dict(zip(main_slate["CleanPlayer"], main_slate["Half PPR Proj"]))
        except Exception:
            st.error("ETR projections file not found or malformed.")
            proj_lookup = {}
    
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
    
        # Keep an unfiltered copy for global tables
        base_leaderboard_df = leaderboard_df.copy()
    
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
    
        # --- Dashboard 1: Top 100 Team Frequency by User (global, unaffected by user filter) ---
        st.markdown("### 📊 Top 100 Team Frequency by User")
    
        top_100_df = base_leaderboard_df.sort_values("Projected Points", ascending=False).head(100)
        top_counts = top_100_df["User"].value_counts().reset_index()
        top_counts.columns = ["User", "Top 100 Teams"]
    
        total_counts = base_leaderboard_df["User"].value_counts().reset_index()
        total_counts.columns = ["User", "Total Teams"]
    
        user_summary = pd.merge(total_counts, top_counts, on="User", how="left").fillna(0)
        user_summary["Top 100 Teams"] = user_summary["Top 100 Teams"].astype(int)
        user_summary["% in Top 100"] = (user_summary["Top 100 Teams"] / user_summary["Total Teams"] * 100).round(2)
    
        styled_summary = user_summary.sort_values("Top 100 Teams", ascending=False).style.format({
            "% in Top 100": "{:.2f}"
        }).background_gradient(subset=["Top 100 Teams", "% in Top 100"], cmap="Blues")
        st.dataframe(styled_summary, use_container_width=True)
    
        # --- Dashboard 2: Top 30 Player Frequency and ADP Comparison (global, unaffected by user filter) ---
        st.markdown("### 📊 Top 30 Player Frequency and ADP Comparison")
    
        top_30_df = base_leaderboard_df.sort_values("Projected Points", ascending=False).head(30)
        top_30_teams = df.merge(top_30_df[["Draft", "Team"]], on=["Draft", "Team"])
    
        top_player_counts = top_30_teams.groupby("Player")["Pick"].agg([
            ("Top 30 Appearances", "count"),
            ("Top 30 ADP", "mean")
        ]).reset_index()
    
        overall_adp = df.groupby("Player")["Pick"].mean().reset_index()
        overall_adp.columns = ["Player", "Overall ADP"]
    
        player_summary = pd.merge(top_player_counts, overall_adp, on="Player", how="left")
        player_summary["ADP Delta"] = (player_summary["Overall ADP"] - player_summary["Top 30 ADP"]).round(2)
    
        player_summary = player_summary.sort_values("Top 30 Appearances", ascending=False)
        styled_players = player_summary.style.format({
            "Top 30 ADP": "{:.2f}",
            "Overall ADP": "{:.2f}",
            "ADP Delta": "{:.2f}"
        }).background_gradient(subset=["Top 30 Appearances", "ADP Delta"], cmap="Purples")
        st.dataframe(styled_players, use_container_width=True)

        
    # --- Tab 9: ETR Impact Dashboard ---
    elif selected_tab == "📊 ETR Impact Dashboard":
        st.subheader("📊 ETR Impact Dashboard")
        
        required_cols = ["Player", "Draft", "Pick", "ETR Timing"]
        if all(col in df.columns for col in required_cols):
            df["ETR Timing"] = df["ETR Timing"].astype(str).str.strip().str.replace("-ETR", "").str.title()
            df["CleanPlayer"] = df["Player"].apply(clean_name)
    
            total_drafts = df["Draft"].nunique()
            draft_counts = df.groupby("ETR Timing")["Draft"].nunique().to_dict()
    
            all_players = df["CleanPlayer"].unique()
            all_drafts = df[["Draft", "ETR Timing"]].drop_duplicates()
            full_grid = pd.MultiIndex.from_product(
                [all_players, all_drafts["Draft"]],
                names=["CleanPlayer", "Draft"]
            ).to_frame(index=False)
            full_grid = full_grid.merge(all_drafts, on="Draft", how="left")
    
            merged = full_grid.merge(
                df[["Draft", "CleanPlayer", "Pick"]],
                on=["Draft", "CleanPlayer"],
                how="left"
            )
            merged["Pick"] = merged["Pick"].fillna(72)
    
            grouped = merged.groupby(["CleanPlayer", "ETR Timing"]).agg(
                ADP=("Pick", "mean"),
                Drafted=("Pick", lambda x: (x < 72).sum())
            ).reset_index()
            grouped["Pct Drafted"] = grouped.apply(
                lambda row: row["Drafted"] / draft_counts.get(row["ETR Timing"], 1), axis=1
            )
    
            all_grouped = merged.groupby("CleanPlayer").agg(
                ADP_All=("Pick", "mean"),
                Drafted_All=("Pick", lambda x: (x < 72).sum())
            ).reset_index()
            all_grouped["Pct Drafted_All"] = all_grouped["Drafted_All"] / total_drafts
    
            pivot = grouped.pivot(index="CleanPlayer", columns="ETR Timing", values=["ADP", "Pct Drafted"])
            pivot.columns = ["_".join(col).strip() for col in pivot.columns.values]
    
            rename_map = {
                "ADP_Pre": "ADP_Pre",
                "ADP_Post": "ADP_Post",
                "Pct Drafted_Pre": "Pct_Pre",
                "Pct Drafted_Post": "Pct_Post"
            }
            pivot = pivot.rename(columns={k: v for k, v in rename_map.items() if k in pivot.columns})
    
            summary = pivot.merge(all_grouped, on="CleanPlayer", how="left")
            if "ADP_Post" in summary.columns and "ADP_All" in summary.columns:
                summary["ADP_Diff"] = summary["ADP_Post"] - summary["ADP_All"]
            else:
                summary["ADP_Diff"] = None
    
            if "Pct_Post" in summary.columns and "Pct_Pre" in summary.columns:
                summary["Pct_Diff"] = summary["Pct_Post"] - summary["Pct_Pre"]
            else:
                summary["Pct_Diff"] = None
    
            name_map = df[["CleanPlayer", "Player"]].drop_duplicates()
            summary = summary.merge(name_map, on="CleanPlayer", how="left")
    
            display_cols = [
                "Player", "ADP_Pre", "ADP_Post", "ADP_All", "ADP_Diff",
                "Pct_Pre", "Pct_Post", "Pct Drafted_All", "Pct_Diff"
            ]
            existing_cols = [col for col in display_cols if col in summary.columns]
            summary = summary[existing_cols].sort_values("ADP_Diff", ascending=False)
    
            # --- FIX: Build formatters dynamically ---
            formatters = {}
            if "ADP_Pre" in summary.columns:
                formatters["ADP_Pre"] = "{:.2f}"
            if "ADP_Post" in summary.columns:
                formatters["ADP_Post"] = "{:.2f}"
            if "ADP_All" in summary.columns:
                formatters["ADP_All"] = "{:.2f}"
            if "ADP_Diff" in summary.columns:
                formatters["ADP_Diff"] = "{:.2f}"
            if "Pct_Pre" in summary.columns:
                formatters["Pct_Pre"] = "{:.2%}"
            if "Pct_Post" in summary.columns:
                formatters["Pct_Post"] = "{:.2%}"
            if "Pct Drafted_All" in summary.columns:
                formatters["Pct Drafted_All"] = "{:.2%}"
            if "Pct_Diff" in summary.columns:
                formatters["Pct_Diff"] = "{:.2%}"
    
            styled = summary.style.format(formatters).background_gradient(
                subset=[col for col in ["ADP_Diff", "Pct_Diff"] if col in summary.columns],
                cmap="coolwarm"
            )
    
            st.dataframe(styled, use_container_width=True)
        else:
            st.warning("Required columns not found in the draft data.")


    # --- Tab 10: ADP Change Tracker ---
    elif selected_tab == "📉 ADP Change Tracker":
        st.subheader("📉 ADP Change Tracker")
    
        with st.expander("ℹ️ What do these terms mean?"):
            st.markdown("""
            - **Recent ADP**: Average draft position over the most recent set of drafts.
            - **Earlier ADP**: Average draft position from the previous set of drafts.
            - **ADP Change**: Earlier ADP − Recent ADP. A **positive** value means the player is being drafted **earlier** (rising), while a **negative** value means they’re being drafted **later** (falling).
            - **Velocity**: ADP change per draft — how fast the player's position is shifting.
            - **Recent % Drafted**: % of recent drafts where the player was selected.
            - **Earlier % Drafted**: % of earlier drafts where the player was selected.
            - **Draft Rate Change**: Earlier % − Recent %. A **positive** value means the player is being drafted **less often**, while a **negative** value means they’re being drafted **more often**.
            - **Draft Rate Velocity**: Draft rate change per draft — how fast selection frequency is changing.
            """)
    
        # --- Draft windows ---
        total_drafts = df["Draft"].nunique()
        max_range = min(50, total_drafts - 2)
        draft_window = st.slider("Number of Recent Drafts to Compare", 2, max_range, 5, key="tab10_window")
    
        earlier_window = st.slider(
            "Number of Earlier Drafts to Compare Against",
            min_value=draft_window,
            max_value=min(50, total_drafts - draft_window),
            value=draft_window,
            key="tab10_earlier_window"
        )
    
        sorted_drafts = sorted(df["Draft"].unique())
        recent_drafts = sorted_drafts[-draft_window:]
        earlier_drafts = sorted_drafts[-(draft_window + earlier_window):-draft_window]
    
        all_players = pd.DataFrame(df["Player"].unique(), columns=["Player"])
    
        # --- ADP calculations ---
        adp_recent = df[df["Draft"].isin(recent_drafts)].groupby("Player")["Pick"].mean().reset_index()
        adp_recent.columns = ["Player", "Recent ADP"]
        adp_recent = all_players.merge(adp_recent, on="Player", how="left")
        adp_recent["Recent ADP"] = adp_recent["Recent ADP"].fillna(72)
    
        adp_earlier = df[df["Draft"].isin(earlier_drafts)].groupby("Player")["Pick"].mean().reset_index()
        adp_earlier.columns = ["Player", "Earlier ADP"]
        adp_earlier = all_players.merge(adp_earlier, on="Player", how="left")
        adp_earlier["Earlier ADP"] = adp_earlier["Earlier ADP"].fillna(72)
    
        # --- % Drafted calculations ---
        recent_draft_counts = df[df["Draft"].isin(recent_drafts)].groupby("Player")["Draft"].nunique().reset_index()
        recent_draft_counts.columns = ["Player", "Recent Drafts"]
        recent_draft_counts = all_players.merge(recent_draft_counts, on="Player", how="left")
        recent_draft_counts["Recent Drafts"] = recent_draft_counts["Recent Drafts"].fillna(0)
        recent_draft_counts["Recent % Drafted"] = (recent_draft_counts["Recent Drafts"] / draft_window * 100).round(2)
    
        earlier_draft_counts = df[df["Draft"].isin(earlier_drafts)].groupby("Player")["Draft"].nunique().reset_index()
        earlier_draft_counts.columns = ["Player", "Earlier Drafts"]
        earlier_draft_counts = all_players.merge(earlier_draft_counts, on="Player", how="left")
        earlier_draft_counts["Earlier Drafts"] = earlier_draft_counts["Earlier Drafts"].fillna(0)
        earlier_draft_counts["Earlier % Drafted"] = (earlier_draft_counts["Earlier Drafts"] / earlier_window * 100).round(2)
    
        # --- Merge all metrics ---
        merged = all_players.merge(adp_recent, on="Player")
        merged = merged.merge(adp_earlier, on="Player")
        merged = merged.merge(recent_draft_counts[["Player", "Recent % Drafted"]], on="Player")
        merged = merged.merge(earlier_draft_counts[["Player", "Earlier % Drafted"]], on="Player")
    
        merged["ADP Change"] = (merged["Earlier ADP"] - merged["Recent ADP"]).round(2)
        merged["Velocity"] = (merged["ADP Change"] / draft_window).round(2)
        merged["Draft Rate Change"] = (merged["Earlier % Drafted"] - merged["Recent % Drafted"]).round(2)
        merged["Draft Rate Velocity"] = (merged["Draft Rate Change"] / draft_window).round(2)
    
        # --- Add position and team ---
        position_map = df[["Player", "Position"]].drop_duplicates()
        team_map = df[["Player", "NFL_Team"]].drop_duplicates()
        merged = merged.merge(position_map, on="Player", how="left")
        merged = merged.merge(team_map, on="Player", how="left")
    
        # --- Filters ---
        selected_positions = st.multiselect(
            "Filter by Position",
            sorted(df["Position"].dropna().unique()),
            default=sorted(df["Position"].dropna().unique()),
            key="tab10_position"
        )
        merged = merged[merged["Position"].isin(selected_positions)]
    
        min_velocity = st.slider("Minimum ADP Velocity", 0.0, 5.0, 0.5, step=0.1, key="tab10_velocity")
        min_draft_rate_velocity = st.slider("Minimum Draft Rate Velocity", 0.0, 10.0, 0.0, step=0.5, key="tab10_draft_velocity")
        min_recent_drafted_pct = st.slider("Minimum % of Recent Drafts", 0.0, 100.0, 0.0, step=1.0, key="tab10_recent_drafted_pct")
    
        filtered_df = merged[
            ((merged["Velocity"].abs() >= min_velocity) |
             (merged["Draft Rate Velocity"].abs() >= min_draft_rate_velocity)) &
            (merged["Recent % Drafted"] >= min_recent_drafted_pct)
        ]
    
        # --- Player search ---
        player_search = st.text_input("Search for a specific player (optional)", key="tab10_player_search")
        if player_search:
            clean_search = clean_name(player_search)
            filtered_df = filtered_df[
                filtered_df["Player"].apply(clean_name).str.contains(clean_search)
            ]
    
        st.write(f"Filtered players: {len(filtered_df)}")
    
        view_mode = st.radio("View mode", ["Table", "Editor"], horizontal=True, key="tab10_view_mode")
    
        if not filtered_df.empty:
            sorted_df = filtered_df.sort_values("Velocity", ascending=False)
    
            if view_mode == "Table":
                styled_df = sorted_df.style.background_gradient(
                    subset=["Velocity"], cmap="coolwarm"
                ).background_gradient(
                    subset=["Draft Rate Velocity"], cmap="YlOrBr"
                ).format({
                    "Recent ADP": "{:.2f}",
                    "Earlier ADP": "{:.2f}",
                    "ADP Change": "{:.2f}",
                    "Velocity": "{:.2f}",
                    "Recent % Drafted": "{:.2f}",
                    "Earlier % Drafted": "{:.2f}",
                    "Draft Rate Change": "{:.2f}",
                    "Draft Rate Velocity": "{:.2f}"
                })
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.data_editor(
                    sorted_df,
                    use_container_width=True,
                    height=900,
                    column_config={
                        "Recent ADP": st.column_config.NumberColumn(format="%.2f"),
                        "Earlier ADP": st.column_config.NumberColumn(format="%.2f"),
                        "ADP Change": st.column_config.NumberColumn(format="%.2f"),
                        "Velocity": st.column_config.NumberColumn(format="%.2f"),
                        "Recent % Drafted": st.column_config.NumberColumn(format="%.2f"),
                        "Earlier % Drafted": st.column_config.NumberColumn(format="%.2f"),
                        "Draft Rate Change": st.column_config.NumberColumn(format="%.2f"),
                        "Draft Rate Velocity": st.column_config.NumberColumn(format="%.2f")
                    }
                )
        else:
            st.warning("No players meet the current filters.")

    # --- Tab 11: User Draft Teams ---
    elif selected_tab == "📋 User Draft Teams":
        st.subheader("📋 User Draft Teams")
    
        # --- Load ETR projections ---
        try:
            etr_df = pd.read_csv("data/ETR Projections.csv")  # <-- fixed delimiter
            etr_main = etr_df[etr_df["Slate"].str.upper() == "MAIN"].copy()
            etr_main["CleanPlayer"] = etr_main["Player"].apply(clean_name)
            proj_lookup = dict(zip(etr_main["CleanPlayer"], etr_main["Half PPR Proj"]))
        except Exception as e:
            st.warning(f"ETR projections file not found or malformed: {e}")
            proj_lookup = {}
    
        # --- User selection ---
        all_users = sorted(df["User"].dropna().unique())
        selected_user = st.selectbox("Select a User", all_users, key="tab11_user_select")
    
        user_df = df[df["User"] == selected_user].copy()
        user_df = user_df.sort_values(["Draft", "Team", "Pick"])
    
        # --- Optional player filter ---
        all_players = sorted(user_df["Player"].dropna().unique())
        selected_players = st.multiselect("Filter by Player(s)", all_players, key="tab11_player_filter")
    
        # --- Group by Draft and Team ---
        grouped = user_df.groupby(["Draft", "Team"])
        roster_rows = []
    
        for (draft_id, team_id), group in grouped:
            group = group.sort_values("Pick")
            team_players = set(group["Player"])
    
            # Filter: skip teams that don't include all selected players
            if selected_players and not all(p in team_players for p in selected_players):
                continue
    
            used_players = set()
    
            def get_first(pos):
                for _, row in group.iterrows():
                    if row["Position"] == pos and row["Player"] not in used_players:
                        used_players.add(row["Player"])
                        return f"{row['Player']} (Pick {row['Pick']})"
                return ""
    
            def get_next_flex():
                for _, row in group.iterrows():
                    if row["Position"] in ["RB", "WR", "TE"] and row["Player"] not in used_players:
                        used_players.add(row["Player"])
                        return f"{row['Player']} (Pick {row['Pick']})"
                return ""
    
            qb = get_first("QB")
            rb = get_first("RB")
            wr1 = get_first("WR")
            wr2 = get_first("WR")
            te = get_first("TE")
            flex = get_next_flex()
    
            # Calculate team ETR projection
            team_players_list = [qb, rb, wr1, wr2, te, flex]
            # Extract clean names (strip "(Pick #)")
            team_proj = sum(
                proj_lookup.get(clean_name(p.split(" (Pick")[0]), 0)
                for p in team_players_list if p
            )
    
            roster_rows.append({
                "Draft": draft_id,
                "Team": team_id,
                "QB": qb,
                "RB": rb,
                "WR1": wr1,
                "WR2": wr2,
                "TE": te,
                "Flex": flex,
                "ETR Projection": round(team_proj, 2)
            })
    
        roster_df = pd.DataFrame(roster_rows).sort_values("Draft", ascending=False)
    
        st.write(f"Total teams drafted by `{selected_user}` matching filter: {len(roster_df)}")
    
        if not roster_df.empty:
            styled = roster_df.style.background_gradient(
                subset=["ETR Projection"], cmap="Greens"
            ).format({"ETR Projection": "{:.2f}"})
            st.dataframe(styled, use_container_width=True)
        else:
            st.info("No teams match the selected filters.")

    
else:
    st.warning("Please log in to access the dashboard.")

