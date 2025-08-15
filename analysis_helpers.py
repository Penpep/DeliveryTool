from delivery_helpers import generate_deliveries, get_dock_inventory_peaks_per_part
import pandas as pd
import math
from datetime import datetime
from openpyxl import load_workbook
import io


def build_time_columns(time_1, time_2):
    columns = ['Part Number', 'Package Type', 'Description', 'Pack Size']
    columns += [f"Delivery {i+1} (S1 - {t.strftime('%I:%M %p')})" for i, t in enumerate(time_1)]
    columns += [f"Delivery {i+1} (S2 - {t.strftime('%I:%M %p')})" for i, t in enumerate(time_2)]
    return columns

def build_delivery_plan(df_bom, inventory_on_hand, move_order_prev, time_1, time_2, shift_1_hours, shift_2_hours, buffer_rate):
    delivery_plan = []

    for _, row in df_bom.iterrows():
        part = row['Part Number']
        pkg_type = row['Package Type']
        pack_size = row['Standard Pack Size']
        descrip = row['Description']
        qty1 = row['Quantity Needed for Shift 1']
        qty2 = row['Quantity Needed for Shift 2']
        cons_1 = row['Consumption Rate Units/ Hour Shift 1']
        cons_2 = row['Consumption Rate / Hour Shift 2']
        move_order_prev_Day = row['Total Move Order - Prev Day'] 
        total_qty_needed_previous_Day= row['Total QTY Needed Previous Day']

        # === Get current inventory for this part ===
        on_hand_qty = inventory_on_hand.get(part, row['On-hand qty'])
        # === Get MO qty from previous day === 
        move_order_prev_Day = move_order_prev.get(part, row['Total Move Order - Prev Day'])

        # === Calculate available qty before shift 1 ===
        
        available_on_hand_shift1 = on_hand_qty + move_order_prev_Day - total_qty_needed_previous_Day if move_order_prev_Day != 0 else on_hand_qty

        # === Generate shift 1 deliveries ===
        deliveries_1, on_hand_after_1 = generate_deliveries(
            qty1, pack_size, len(time_1), shift_1_hours, cons_1,
            available_on_hand_shift1, buffer_rate
        )

        # === Generate shift 2 deliveries ===
        deliveries_2, on_hand_after_2 = generate_deliveries(
            qty2, pack_size, len(time_2), shift_2_hours, cons_2,
            on_hand_after_1, buffer_rate
        )

        # === Update inventory tracking ===
        inventory_on_hand[part] = on_hand_after_2
        # maybe update move_order_prev_Day to 0 to avoid double counting for duplicate BOM parts 
        move_order_prev[part] = 0 

        # === Record output row ===
        delivery_plan.append([part, pkg_type, descrip, pack_size] + deliveries_1 + deliveries_2)

    columns = build_time_columns(time_1, time_2)
    df_output = pd.DataFrame(delivery_plan, columns=columns)
    df_output = df_output.groupby(['Part Number', 'Package Type', 'Description', 'Pack Size'], as_index=False).sum(numeric_only=True)
    return df_output

def build_dock_space_analysis(df_bom, df_output, dock_on_hand, time_1, time_2, shift_1_hours, shift_2_hours, num_of_lines_1, num_of_lines_2):
    space_records = []

    for _, row in df_bom.iterrows():
        part = row['Part Number']
        pack_size = row['Standard Pack Size']
        pkg_type = row['Package Type']
        cons_1 = row['Consumption Rate Units/ Hour Shift 1'] * 0.9
        cons_2 = row['Consumption Rate / Hour Shift 2'] * 0.9
        max_lineside_qty_1 = row['Maximum Storage on Lineside'] * num_of_lines_1
        max_lineside_qty_2 = row['Maximum Storage on Lineside'] * num_of_lines_2
        min_lineside_qty_1 = row['Minimum Storage on Lineside'] * num_of_lines_1
        min_lineside_qty_2 = row['Minimum Storage on Lineside'] * num_of_lines_2

        on_hand_on_lineside = row['On-hand QTY at Lineside'] # drive unit specific 


    # Use updated dock stock from inventory_on_hand
        on_dock = dock_on_hand.get(part, row['On-hand on dock']) if dock_on_hand else row['On-hand on dock']
        lineside_stock = on_hand_on_lineside  

    # Get delivery rows explicitly by Part Number
        df_row = df_output[df_output['Part Number'] == part]
        deliveries_1 = df_row.loc[:, df_output.columns.str.contains(r"S1 -")].sum().tolist()
        deliveries_2 = df_row.loc[:, df_output.columns.str.contains(r"S2 -")].sum().tolist()

        timeline_1, lineside2, dock2 = get_dock_inventory_peaks_per_part(
            deliveries_1, pack_size, cons_1, shift_1_hours,
            on_dock, lineside_stock, max_lineside_qty_1, min_lineside_qty_1
        )

        timeline_2, _, final_dock = get_dock_inventory_peaks_per_part(
            deliveries_2, pack_size, cons_2, shift_2_hours,
            dock2, lineside2, max_lineside_qty_2, min_lineside_qty_2
        )

        dock_on_hand[part] = final_dock 

        for i, inv in enumerate(timeline_1):
            space_records.append({
                'Part Number': part,
                'Shift': 1,
                'Delivery Label': f"Delivery {i+1} (S1 - {time_1[i].strftime('%I:%M %p')})",
                'Inventory Packages': inv,
                'Package Type': pkg_type
            })
        for i, inv in enumerate(timeline_2):
            space_records.append({
                'Part Number': part,
                'Shift': 2,
                'Delivery Label': f"Delivery {i+1} (S2 - {time_2[i].strftime('%I:%M %p')})",
                'Inventory Packages': inv,
                'Package Type': pkg_type
            })

    df_space = pd.DataFrame(space_records)

    flat_records = []
    part_order = df_bom['Part Number'].tolist()

    for part in part_order:
        part_rows = df_space[df_space['Part Number'] == part]
        if part_rows.empty:
            continue
        pkg_type = part_rows['Package Type'].iloc[0]
        row = {'Part Number': part, 'Package Type': pkg_type, 'Description': df_bom[df_bom['Part Number'] == part]['Description'].iloc[0], 'Pack Size': df_bom[df_bom['Part Number'] == part]['Standard Pack Size'].iloc[0]}
        for _, rec in part_rows.iterrows():
            row[rec['Delivery Label']] = rec['Inventory Packages']
        flat_records.append(row)

    df_dock_space = pd.DataFrame(flat_records).fillna(0) 
    return df_dock_space

def append_summary_rows(df_dock_space, box_dock_space, side_lane_pallet, pallet_per_lane, side_lane, lane, rack):

    df_boxes = df_dock_space[df_dock_space['Package Type'] == 'Box']
    df_pallets = df_dock_space[df_dock_space['Package Type'] == 'Pallet']

    box_sums = df_boxes.iloc[:, 4:].sum()
    pallet_sums = df_pallets.iloc[:, 4:].sum()

    df_dock_space.loc[len(df_dock_space)] = ['TOTAL - BOX', 'Box', '', ''] + list(box_sums)
    df_dock_space.loc[len(df_dock_space)] = ['TOTAL - PALLET', 'Pallet', '', ''] + list(pallet_sums)

    # --- RACK ---
    rack_df = df_dock_space[df_dock_space['Part Number'].isin(rack)]
    rack_sums = rack_df.iloc[:, 4:].sum()
    df_dock_space.loc[len(df_dock_space)] = ['TOTAL - RACK BOXES', '', '', ''] + list(rack_sums)
    df_dock_space.loc[len(df_dock_space)] = ['PALLET RACK % Usage', '', '', ''] + list(((rack_sums / box_dock_space) * 100).round(2))
    df_dock_space.loc[len(df_dock_space)] = pd.Series(dtype=object)
    
   # --- SIDE LANE ---
    side_df = df_dock_space[df_dock_space['Part Number'].isin(side_lane)].copy()

    # Convert boxes to pallet spots
    for part in side_lane:
        mask = df_dock_space['Part Number'] == part
        for col in df_dock_space.columns[4:]:
            df_dock_space.loc[mask, col] = df_dock_space.loc[mask, col].apply(lambda x: 1 if 0 < x <= 60 else math.ceil(x / 60))

    # Sum pallets for side lane
    side_sums = side_df.iloc[:, 4:].sum()
    df_dock_space.loc[len(df_dock_space)] = ['SIDE LANE % Usage', '', '', ''] + list(((side_sums / side_lane_pallet) * 100).round(2))
    df_dock_space.loc[len(df_dock_space)] = pd.Series(dtype=object)

    # --- LANE ----
    lane_df = df_dock_space[df_dock_space['Part Number'].isin(lane)].copy()
    for idx, row in lane_df.iterrows():
        part = row['Part Number']
        pkg_type = row['Package Type']
        desc = row['Description']
        timeline = row.iloc[4:]
        usage_pct = (timeline / pallet_per_lane) * 100
        label = f"LANE % - {part}"
        row_to_add = [label, pkg_type, desc, ''] + list(usage_pct)

        # Pad/trim if needed
        if len(row_to_add) < len(df_dock_space.columns):
            row_to_add += [''] * (len(df_dock_space.columns) - len(row_to_add))
        elif len(row_to_add) > len(df_dock_space.columns):
            row_to_add = row_to_add[:len(df_dock_space.columns)]

        df_dock_space.loc[len(df_dock_space)] = row_to_add
    
    # --- Add total pallet usage----
    MRB_total_pallet_space = 25 #CHANGE THIS
    total_pallet_space = side_lane_pallet + pallet_per_lane * 12 + MRB_total_pallet_space
    interval_pallet_usage = round((pallet_sums / total_pallet_space) * 100, 2)

    df_dock_space.loc[len(df_dock_space)] = ['TOTAL PALLET % USAGE', '', '', ''] + list(interval_pallet_usage)

    return df_dock_space
