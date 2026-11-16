"""Material tables and shop rates.

Every number here is a starting guess. calibrate.py tells you how far
off they are compared with real quotes.
"""

PRINT_MATERIALS = {
    # density in g/cm3, filament price in $/g
    "PLA": {"density": 1.24, "price_per_g": 0.025},
    "PETG": {"density": 1.27, "price_per_g": 0.030},
    "Nylon": {"density": 1.14, "price_per_g": 0.060},
}

CNC_MATERIALS = {
    # density in g/cm3, bar-stock price in $/g, how fast a mill removes it
    "Aluminium 6061": {"density": 2.70, "price_per_g": 0.005, "removal_cm3_per_h": 600},
    "Delrin (POM)": {"density": 1.41, "price_per_g": 0.015, "removal_cm3_per_h": 900},
    "Steel 1018": {"density": 7.87, "price_per_g": 0.003, "removal_cm3_per_h": 150},
}

# 3D printing shop rates
PRINT_RATE_CM3_PER_H = 15.0     # plastic a printer lays down per hour
PRINT_MACHINE_PER_H = 2.0       # $ per printer-hour
PRINT_SETUP = 5.0               # $ per job
CLEANUP_PER_CM2 = 0.05          # $ to remove support, per cm2 it touches

# CNC shop rates
CNC_MACHINE_PER_H = 75.0
CNC_SETUP = 60.0                # $ for the first setup (fixturing, toolpaths)
CNC_EXTRA_SETUP = 25.0          # $ for each extra side the part is flipped to
THIN_WALL_COST_PER_MM2 = 0.02   # $ per mm2 of thin wall (slow, careful passes)

# Overall correction factors. calibrate.py suggests values for these.
PRINT_PRICE_FACTOR = 1.0
CNC_PRICE_FACTOR = 1.0