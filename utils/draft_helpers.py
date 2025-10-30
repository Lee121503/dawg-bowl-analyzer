import pandas as pd
from collections import Counter

def calculate_adp(df):
    total_drafts = df["Draft"].nunique()
    all_players = df["Player"].dropna().unique()

    # Map each player to their list of picks
    player_picks = df.groupby("Player")["Pick"].apply(list).to_dict()

    adp_data = []
    for player in all_players:
        picks = player_picks.get(player, [])
        missing_drafts = total_drafts - len(picks)
        all_picks = picks + [72] * missing_drafts
        adp = sum(all_picks) / total_drafts
        adp_data.append({"Player": player, "Average Draft Position": adp})

    return pd.DataFrame(adp_data)

def detect_stacks(df):
    stack_data = []

    grouped = df.groupby(["Draft", "Team"])["Player"].apply(list).reset_index()

    for _, row in grouped.iterrows():
        draft = row["Draft"]
        team = row["Team"]
        players = row["Player"]

        # Safely extract team codes from player names
        team_counts = Counter([str(p).split()[0] for p in players if pd.notna(p)])

        stack_data.append({
            "Draft": draft,
            "Team": team,
            "Stacks": dict(team_counts)
        })

    return pd.DataFrame(stack_data)

def find_combos(df):
    # Placeholder for future combo detection logic
    return pd.DataFrame()

