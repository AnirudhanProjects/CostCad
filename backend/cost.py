import sys
import trimesh

# Placeholder constants. We'll tune these against real quotes later.
PLA_DENSITY, PLA_PRICE_PER_G = 1.24, 0.025      # g/cm3, $/g
ALU_DENSITY, ALU_PRICE_PER_G = 2.70, 0.005      # g/cm3, $/g
PRINT_RATE_CM3_PER_H, PRINT_MACHINE_PER_H = 15.0, 2.0
CNC_REMOVAL_CM3_PER_H, CNC_MACHINE_PER_H = 600.0, 75.0
CNC_SETUP, PRINT_SETUP = 60.0, 5.0
SUPPORT_COST_PER_MM2 = 0.01     # $ per mm2 of overhang (support + cleanup)
THIN_WALL_COST_PER_MM2 = 0.02   # $ per mm2 of thin wall (slow machining)


def print_cost(mesh, qty=1, overhang_area=0.0):
    vol = mesh.volume / 1000                    # mm3 -> cm3
    material = vol * PLA_DENSITY * PLA_PRICE_PER_G
    machine = (vol / PRINT_RATE_CM3_PER_H) * PRINT_MACHINE_PER_H
    support = overhang_area * SUPPORT_COST_PER_MM2
    return material + machine + support + PRINT_SETUP / qty


def cnc_cost(mesh, qty=1, thin_area=0.0):
    ex = mesh.extents + 10                      # 5 mm stock margin per side
    stock = (ex[0] * ex[1] * ex[2]) / 1000      # cm3
    removed = stock - mesh.volume / 1000
    material = stock * ALU_DENSITY * ALU_PRICE_PER_G
    machine = (removed / CNC_REMOVAL_CM3_PER_H) * CNC_MACHINE_PER_H
    thin_penalty = thin_area * THIN_WALL_COST_PER_MM2
    return material + machine + thin_penalty + CNC_SETUP / qty


if __name__ == "__main__":
    mesh = trimesh.load(sys.argv[1], force="mesh")
    print("3D print (PLA):  $", round(print_cost(mesh), 2))
    print("CNC (aluminium): $", round(cnc_cost(mesh), 2))