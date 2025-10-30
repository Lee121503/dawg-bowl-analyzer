import pandas as pd

def load_etr_projections(csv_path="data/etr_fd_main.csv"):
    try:
        df = pd.read_csv(csv_path)

        # Clean column names
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        # Rename key columns for consistency
        df.rename(columns={
            "player": "name",
            "pos": "position",       # DK format
            "fd_pos": "position",    # FD format
            "opp": "opponent"
        }, inplace=True)

        # Estimate FanDuel half PPR projection (placeholder)
        if "fd_proj" not in df.columns and "dk_proj" in df.columns:
            df["fd_proj"] = df["dk_proj"] - 1.0  # crude adjustment until receptions are available

        return df

    except Exception as e:
        print(f"Error loading ETR projections: {e}")
        return pd.DataFrame()

def aggregate_team_position_projections(df):
    if df.empty:
        print("❌ Cannot aggregate: DataFrame is empty.")
        return pd.DataFrame()

    required = {"team", "position", "fd_proj"}
    if not required.issubset(df.columns):
        print(f"❌ Missing columns: {required - set(df.columns)}")
        return pd.DataFrame()

    # Group and aggregate FanDuel projections
    agg_df = (
        df.groupby(["team", "position"], as_index=False)
        .agg(total_proj=("fd_proj", "sum"))
        .sort_values(by="total_proj", ascending=False)
    )

    return agg_df
