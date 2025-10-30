from data_helpers import load_etr_projections, aggregate_team_position_projections

def main():
    print("📊 Loading ETR projections...")
    etr_df = load_etr_projections()

    if etr_df.empty:
        print("❌ Failed to load projections.")
        return

    print("✅ Projections loaded. Preview:")
    print(etr_df.head())

    print("\n📋 Columns in ETR DataFrame:")
    print(etr_df.columns.tolist())

    print("\n📊 Aggregating by team and position (half PPR)...")
    agg_df = aggregate_team_position_projections(etr_df)

    if agg_df.empty:
        print("❌ Aggregation failed.")
    else:
        print("✅ Aggregation complete. Top stacks:")
        print(agg_df.head(10))

if __name__ == "__main__":
    main()

