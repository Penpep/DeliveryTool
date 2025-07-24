import math

def generate_times(start, end, cadence):
    if cadence == 0 or cadence is None:
        return []  # No deliveries
    interval = (end - start) / cadence
    return [start + i * interval for i in range(cadence)]

def generate_deliveries(qty, pack_size, cadence, shft_hrs, cons_rate, on_hand):
    if not cadence:
        return []

    deliveries = []
    interval = shft_hrs / cadence
    available_on_hand = on_hand
    consumed = 0

    for _ in range(cadence):
        interval_consumption = cons_rate * interval

        # Remaining demand for the full shift
        remaining_demand = max(qty - consumed, 0)
        # Only consume up to remaining demand for this interval
        interval_demand = min(interval_consumption, remaining_demand)

        if interval_demand <= 0:
            deliveries.append(0)
            continue
        
        # 0 delivery if enough on hand. update on hand and consumption then go next cadnece
        if available_on_hand >= interval_demand:
            available_on_hand -= interval_demand
            consumed += interval_demand
            deliveries.append(0)
            continue

        # Deliver to cover shortfall (60 demand but 8 available == shortfall of 52)
        shortfall = interval_demand - available_on_hand
        #round up pack size- never have delivery of 5 chassis for example
        packs_needed = math.ceil(shortfall / pack_size)
        deliver_now = packs_needed * pack_size

        # append shortfall delviery and update everything 
        deliveries.append(deliver_now)
        available_on_hand += deliver_now - interval_demand
        consumed += interval_demand

    return deliveries, available_on_hand

def get_dock_inventory_peaks_per_part(deliveries, pack_size, consumption_rate, total_shift_hours, 
                                      on_hand_dock, on_hand_lineside, max_lineside_qty):
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
        if lineside_inventory_units < max_lineside_qty:
            refill_needed = max_lineside_qty - lineside_inventory_units
            refill_from_dock = min(refill_needed, dock_inventory_units)
            dock_inventory_units -= refill_from_dock
            lineside_inventory_units += refill_from_dock

    return dock_timeline, lineside_inventory_units, dock_inventory_units