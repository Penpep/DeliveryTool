from delivery_helpers import generate_deliveries, get_dock_inventory_peaks_per_part

import tkinter as tk
from tkinter import filedialog
from openpyxl.styles import PatternFill
import pandas as pd


output = generate_deliveries(225, 24, 4, 8, 30, 188)
output2 = generate_deliveries(65, 24, 4, 8, 8, 188)

print(output) 
print(output2)