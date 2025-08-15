import math
from drive_specifics import get_lane_material
from datetime import datetime, timedelta

def generate_times(start, shift_hours, cadence):
    if cadence == 0 or cadence is None:
        return []

    interval = shift_hours / cadence  # hours per interval

    return [start + timedelta(hours=interval * i) for i in range(cadence)]

def generate_deliveries(qty, pack_size, cadence, shft_hrs, cons_rate, available_on_hand, buffer_rate):
    if not cadence:
        return [], available_on_hand

    deliveries = []
    interval = shft_hrs / cadence
    consumed = 0

    qty = qty * buffer_rate #15 percent buffer -> just increase the demand by 15 percent
    cons_rate = cons_rate * buffer_rate #15 percent buffer -> just increase the consumption rate by 15 percent

    #This is for checking NUMBERS!!! only will see in terminal on VSCODE
    print(f"Generating deliveries for qty: {qty}, pack_size: {pack_size}, cadence: {cadence}, shift_hours: {shft_hrs}, consumption_rate: {cons_rate}, available_on_hand: {available_on_hand}")

    for _ in range(cadence):
        interval_consumption = cons_rate * interval

        # Remaining demand for the full shift
        remaining_demand = max(qty - consumed, 0)
        interval_demand = min(interval_consumption, remaining_demand)

        if interval_demand <= 0: 
            deliveries.append(0)
            continue

        # If there's enough inventory. Add buffer, no delivery needed
        if available_on_hand >= interval_demand:
            available_on_hand -= interval_demand
            consumed += interval_demand
            deliveries.append(0)
            continue

        # Otherwise, deliver shortfall (include buffer), round to pack size 
        shortfall = interval_demand - available_on_hand

        packs_needed = math.ceil(shortfall / pack_size)
        deliver_now = packs_needed * pack_size

        deliveries.append(deliver_now)

        # Update available_on_hand after delivery and consumption
        available_on_hand += deliver_now
        available_on_hand -= interval_demand
        consumed += interval_demand

    return deliveries, available_on_hand

#With minimum storage on lineside 

def get_dock_inventory_peaks_per_part(deliveries, pack_size, consumption_rate, total_shift_hours, 
                                      on_hand_dock, on_hand_lineside, max_lineside_qty, min_lineside_qty):
    #Guard against 0 cadence 
    if not deliveries or len(deliveries) == 0:
        return [], on_hand_lineside, 0

    dock_inventory_units = on_hand_dock
    lineside_inventory_units = on_hand_lineside

    dock_timeline = []

    interval_hours = total_shift_hours / len(deliveries)

    for delivery in deliveries:
        # Deliver to dock
        delivered_units = delivery
        dock_inventory_units += delivered_units

        # Record dock peak (after delivery, before anything else)
        dock_timeline.append(math.ceil(dock_inventory_units / pack_size))

        # Consumption for this interval
        interval_consumption = consumption_rate * interval_hours

        # Line consumes from lineside first
        if lineside_inventory_units >= interval_consumption:
            lineside_inventory_units -= interval_consumption
        else:
            deficit = interval_consumption - lineside_inventory_units
            lineside_inventory_units = 0
            # Pull remaining needed from dock
            pull_from_dock_for_consumption = min(deficit, dock_inventory_units)
            dock_inventory_units -= pull_from_dock_for_consumption
            deficit -= pull_from_dock_for_consumption

        # Refill buffer to target (if possible)
        if lineside_inventory_units <= min_lineside_qty:
            refill_needed = max_lineside_qty - lineside_inventory_units
            refill_from_dock = min(refill_needed, dock_inventory_units)
            dock_inventory_units -= refill_from_dock
            lineside_inventory_units += refill_from_dock

    return dock_timeline, lineside_inventory_units, dock_inventory_units