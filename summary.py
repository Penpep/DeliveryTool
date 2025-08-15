
import pandas as pd
import numpy as np


import pandas as pd
import numpy as np

def summary_delivery(filename, units_to_plan):
    delivery_dfs = []

    for unit in units_to_plan: 
        df = pd.read_excel(filename, sheet_name=f"{unit}-Delivery")
        df['Drive Unit'] = unit
        delivery_dfs.append(df)

    combined = pd.concat(delivery_dfs, ignore_index=True)
    delivery_cols = [col for col in combined.columns if 'Delivery' in col]

    # Convert to pack counts
    for col in delivery_cols:
        combined[f"{col} (Packs)"] = np.ceil(combined[col] / combined['Pack Size'])

    # Convert to pallets
    is_box = combined['Package Type'].str.lower() == 'box'
    is_conveyor = combined['Part Number'].astype(str).str.strip() == "400-03632"

    for col in delivery_cols:
        pack_col = f"{col} (Packs)"
        combined[col] = combined[pack_col]  # default pallets = packs
        combined.loc[is_box, col] = np.ceil(combined.loc[is_box, pack_col] / 10)
        combined.loc[is_conveyor, col] *= 2  # conveyor counts double

    # Group by part
    grouped = combined.groupby(['Part Number', 'Pack Size', 'Package Type'], as_index=False)[delivery_cols].sum()

    # Append total row (sum of pallet deliveries per slot)
    total_row = {col: grouped[col].sum() if col in delivery_cols else '' for col in grouped.columns}
    total_row['Part Number'] = 'TOTAL - Pallets'
    grouped = pd.concat([grouped, pd.DataFrame([total_row])], ignore_index=True)

    return grouped









