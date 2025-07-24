
import pandas as pd
import numpy as np

# def summary_delivery(filename, units_to_plan):
#     import pandas as pd
#     import numpy as np

#     delivery_dfs = []

#     for unit in units_to_plan: 
#         df = pd.read_excel(filename, sheet_name=f"{unit}-Delivery")
#         df['Drive Unit'] = unit
#         delivery_dfs.append(df)

#     combined_deliveries = pd.concat(delivery_dfs, ignore_index=True)

#     # Identify delivery columns
#     delivery_cols = [col for col in combined_deliveries.columns if 'Delivery' in col]

#     # Create total row in pallets
#     total_row = {
#         'Part Number': 'TOTAL',
#         'Drive Unit': '',
#         'Package Type': '',
#         'Description': '',
#         'Pack Size': ''
#     }

#     # Boolean masks
#     is_box = combined_deliveries['Package Type'].str.lower() == 'box'
#     is_conveyor = combined_deliveries['Part Number'].str.strip().str.lower() == '400-03632'

#     for col in delivery_cols:
#         units = combined_deliveries[col]
#         packs = np.ceil(units / combined_deliveries['Pack Size'])
#         pallets = np.where(is_box, np.ceil(packs / 10), packs)
#         pallets = np.where(is_conveyor, pallets * 2, pallets)
#         total_row[col] = pallets.sum()

#     # Append the total row
#     summary_df = pd.concat([combined_deliveries, pd.DataFrame([total_row])], ignore_index=True)

#     return summary_df

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


# Since simplified logic is just pull all parts from part A first, we can rearrange combined delivery dataframe by 
# highest consumption rate and smaller pack size   

def rearrange_priority(balanced_df, df_bom, shift_rate_col, con_dscending=False, pack_ascending=True):
    df_sorted = balanced_df.merge(df_bom[['Part Number', shift_rate_col]], on='Part Number', how='left')     
    df_sorted = df_sorted.sort_values(by=[shift_rate_col, 'Pack Size'], ascending=[con_dscending, pack_ascending]).reset_index(drop=True)  
    df_sorted = df_sorted.drop(columns=[shift_rate_col])
    return df_sorted





