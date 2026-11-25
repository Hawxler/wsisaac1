from pathlib import Path
from pxr import Usd, UsdGeom, UsdPhysics, Sdf

SOURCE = Path(
    "/home/hawx/wsisaac1/src/isaac_dobot1/"
    "assets/usd/dobot_pick_place_1cap.usd"
)

OUTPUT = Path(
    "/home/hawx/wsisaac1/src/dobot_reach_lab/"
    "assets/magician_robot_only.usda"
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

source_stage = Usd.Stage.Open(str(SOURCE))
if source_stage is None:
    raise RuntimeError(f"Cannot open {SOURCE}")

robot = source_stage.GetPrimAtPath("/magician")
if not robot.IsValid():
    raise RuntimeError("/magician not found")

# References와 Layer를 합친 USD를 생성한다.
flat_layer = source_stage.Flatten()

output_stage = Usd.Stage.CreateNew(str(OUTPUT))

Sdf.CopySpec(
    flat_layer,
    Sdf.Path("/magician"),
    output_stage.GetRootLayer(),
    Sdf.Path("/magician"),
)

UsdGeom.SetStageMetersPerUnit(
    output_stage,
    UsdGeom.GetStageMetersPerUnit(source_stage),
)
UsdGeom.SetStageUpAxis(
    output_stage,
    UsdGeom.GetStageUpAxis(source_stage),
)

robot_out = output_stage.GetPrimAtPath("/magician")
output_stage.SetDefaultPrim(robot_out)

# 이미 있는 ArticulationRootAPI는 그대로 유지한다.
articulation_roots = [
    str(p.GetPath())
    for p in Usd.PrimRange(robot_out)
    if p.HasAPI(UsdPhysics.ArticulationRootAPI)
]

if not articulation_roots:
    UsdPhysics.ArticulationRootAPI.Apply(robot_out)

output_stage.GetRootLayer().Save()

print("MAGICIAN USD EXPORTED")
print("Output:", OUTPUT)
print("Articulation:", articulation_roots or ["/magician"])