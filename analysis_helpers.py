from delivery_helpers import generate_deliveries, get_dock_inventory_peaks_per_part
import pandas as pd
import math
from datetime import datetime
from openpyxl import load_workbook
import io

def get_lane_material(input_drive_unit): 
    if input_drive_unit == 'Hercules':
        side_lane = [
            "600-01361", "400-01256", "400-01259", "400-01260-C2",
            "600-01051", "600-01248", "600-02000", "600-02018", "600-00986"
        ]
        lane = [
            "400-01318", "400-01950", "600-01020", "600-01035",
            "600-02306", "400-01226-C2", "400-01227-C2"
        ]
    elif input_drive_unit == 'Megasus':
        side_lane = [
            "400-02833", "400-02858-C2", "400-02977-C2", "400-02978-C2",
            "400-02970-C2", "400-02979-C2", "400-03279", "600-02018", "600-01361"\
        ]
        lane = [
            "400-01226-C2", "400-01227-C2", "400-03296", "400-03632", "600-01324",
            "600-01782", "600-02306", "600-02572", "600-02000"
        ]
    elif input_drive_unit == 'Proteus':
        side_lane = ["400-03979", "420-12065", "400-03537"]
        lane = ["400-04392", "600-03241", "600-05057", "600-05059", "400-03791", "400-03792"]
   
    return side_lane, lane 

def build_time_columns(time_1, time_2):
    columns = ['Part Number', 'Package Type', 'Description', 'Pack Size']
    columns += [f"Delivery {i+1} (S1 - {t.strftime('%I:%M %p')})" for i, t in enumerate(time_1)]
    columns += [f"Delivery {i+1} (S2 - {t.strftime('%I:%M %p')})" for i, t in enumerate(time_2)]
    return columns

def build_delivery_plan(df_bom, inventory_on_hand, time_1, time_2, shift_1_hours, shift_2_hours):
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

        overall_onhand = inventory_on_hand.get(part, row['On-hand qty']) if inventory_on_hand else row['On-hand qty']
        total_required = qty1 + qty2
        
        # print(f"{part}: SHIFT 1 CALL → qty={qty1}, pack_size={pack_size}, cadence={len(time_1)}, shift_hrs={shift_1_hours}, cons_rate={cons_1}, on_hand={overall_onhand}")
        if overall_onhand >= total_required:
            deliveries_1 = [0] * len(time_1)
            deliveries_2 = [0] * len(time_2)
            overall_onhand -= total_required
        else:
            deliveries_1, on_hand_1 = generate_deliveries(qty1, pack_size, len(time_1), shift_1_hours, cons_1, overall_onhand)
           
            deliveries_2, on_hand_2 = generate_deliveries(qty2, pack_size, len(time_2), shift_2_hours, cons_2, on_hand_1)
    
            overall_onhand = on_hand_2

            inventory_on_hand[part] = on_hand_2

        delivery_plan.append([part, pkg_type, descrip, pack_size] + deliveries_1 + deliveries_2)

    columns = build_time_columns(time_1, time_2)
    df_output = pd.DataFrame(delivery_plan, columns=columns)
    return df_output


def build_dock_space_analysis(df_bom, df_output, dock_on_hand, time_1, time_2, shift_1_hours, shift_2_hours):
    space_records = []

    for _, row in df_bom.iterrows():
        part = row['Part Number']
        pack_size = row['Standard Pack Size']
        pkg_type = row['Package Type']
        cons_1 = row['Consumption Rate Units/ Hour Shift 1'] * 0.9
        cons_2 = row['Consumption Rate / Hour Shift 2'] * 0.9
        max_lineside_qty = row['Maximum Storage on Lineside']
        on_hand_on_lineside = row['On-hand QTY at Lineside'] # drive unit specific 


    # Use updated dock stock from inventory_on_hand
        on_dock = dock_on_hand.get(part, row['On-hand on dock']) if dock_on_hand else row['On-hand on dock']
        lineside_stock = on_hand_on_lineside  

    # Get delivery rows explicitly by Part Number
        df_row = df_output[df_output['Part Number'] == part]
        deliveries_1 = df_row.loc[:, df_output.columns.str.contains(r"S1 -")].iloc[0].tolist()
        deliveries_2 = df_row.loc[:, df_output.columns.str.contains(r"S2 -")].iloc[0].tolist()

        timeline_1, lineside2, dock2 = get_dock_inventory_peaks_per_part(
            deliveries_1, pack_size, cons_1, shift_1_hours,
            on_dock, lineside_stock, max_lineside_qty
        )

        timeline_2, _, final_dock = get_dock_inventory_peaks_per_part(
            deliveries_2, pack_size, cons_2, shift_2_hours,
            dock2, lineside2, max_lineside_qty
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

def append_summary_rows(df_dock_space, box_dock_space, side_lane_pallet, pallet_per_lane, side_lane, lane):

    df_boxes = df_dock_space[df_dock_space['Package Type'] == 'Box']
    df_pallets = df_dock_space[df_dock_space['Package Type'] == 'Pallet']

    box_sums = df_boxes.iloc[:, 4:].sum()
    pallet_sums = df_pallets.iloc[:, 4:].sum()

    df_dock_space.loc[len(df_dock_space)] = ['TOTAL - BOX', 'Box', '', ''] + list(box_sums)
    df_dock_space.loc[len(df_dock_space)] = ['TOTAL - PALLET', 'Pallet', '', ''] + list(pallet_sums)
    df_dock_space.loc[len(df_dock_space)] = ['Box % Usage', 'Box', '', ''] + list(((box_sums / box_dock_space) * 100).round(2))

    side_df = df_dock_space[df_dock_space['Part Number'].isin(side_lane)]
    side_sums = side_df.iloc[:, 4:].sum()
    df_dock_space.loc[len(df_dock_space)] = ['TOTAL - SIDE LANE', '', '', ''] + list(side_sums)
    df_dock_space.loc[len(df_dock_space)] = ['SIDE LANE % Usage', '', '', ''] + list(((side_sums / side_lane_pallet) * 100).round(2))
    df_dock_space.loc[len(df_dock_space)] = pd.Series(dtype=object)

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
 
    return df_dock_space
