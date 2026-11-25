import omni.usd
import omni.physx
import omni.timeline

from pxr import Usd, UsdGeom, Gf


# =====================================================
# Bottlecap9 : Current Mesh Bounds and Pick Approach
# Execute: Isaac Sim Script Editor
# Simulation: PAUSE after physics settling
# =====================================================

CAP_PATH = "/bottlecap9"
APPROACH_MARGIN = 0.030  # 30 mm above mesh top

stage = omni.usd.get_context().get_stage()
timeline = omni.timeline.get_timeline_interface()

if timeline.is_stopped():
    raise RuntimeError("Click Play, then Pause first.")

cap = stage.GetPrimAtPath(CAP_PATH)

if not cap.IsValid():
    raise RuntimeError("Bottlecap9 not found")

# 1. Current PhysX rigid-body transform
result = omni.physx.get_physx_interface().get_rigidbody_transformation(
    CAP_PATH
)

if not result["ret_val"]:
    raise RuntimeError("PhysX pose unavailable")

p = result["position"]
q = result["rotation"]  # x, y, z, w

# 2. Build the current rigid-body transform
q_usd = Gf.Quatd(
    float(q[3]),
    Gf.Vec3d(float(q[0]), float(q[1]), float(q[2]))
)

cache = UsdGeom.XformCache(Usd.TimeCode.Default())

root_usd = cache.GetLocalToWorldTransform(cap)

# Preserve the original root scale
root_scale = Gf.Transform(root_usd).GetScale()

scale_matrix = Gf.Matrix4d(1.0)
scale_matrix.SetScale(root_scale)

pose_matrix = Gf.Matrix4d(1.0)
pose_matrix.SetRotate(q_usd)
pose_matrix.SetTranslateOnly(
    Gf.Vec3d(float(p[0]), float(p[1]), float(p[2]))
)

root_physics = scale_matrix * pose_matrix

# 3. Read descendant mesh vertices
world_points = []

for prim in Usd.PrimRange(cap):
    if not prim.IsA(UsdGeom.Mesh):
        continue

    mesh = UsdGeom.Mesh(prim)
    points = mesh.GetPointsAttr().Get()

    if not points:
        continue

    mesh_usd = cache.GetLocalToWorldTransform(prim)

    # Mesh-local -> body-local -> PhysX world
    mesh_to_root = mesh_usd * root_usd.GetInverse()
    mesh_to_world = mesh_to_root * root_physics

    for point in points:
        world_points.append(
            mesh_to_world.Transform(
                Gf.Vec3d(
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                )
            )
        )

if not world_points:
    raise RuntimeError("No Mesh vertices found")

# 4. Mesh world bounds
xmin = min(v[0] for v in world_points)
xmax = max(v[0] for v in world_points)

ymin = min(v[1] for v in world_points)
ymax = max(v[1] for v in world_points)

zmin = min(v[2] for v in world_points)
zmax = max(v[2] for v in world_points)

cx = (xmin + xmax) / 2.0
cy = (ymin + ymax) / 2.0

# 5. Preliminary hover target
hover_z = zmax + APPROACH_MARGIN

print("")
print("========================================")
print(" BOTTLECAP9 TARGET")
print("========================================")

print(
    f"PHYSX BODY ORIGIN : "
    f"{float(p[0]):.4f}, "
    f"{float(p[1]):.4f}, "
    f"{float(p[2]):.4f}"
)

print(f"MESH CENTER XY : {cx:.4f}, {cy:.4f}")
print(f"MESH BOTTOM Z  : {zmin:.4f}")
print(f"MESH TOP Z     : {zmax:.4f}")
print(f"MESH HEIGHT    : {(zmax-zmin)*1000:.2f} mm")

print("")
print("PRELIMINARY HOVER TARGET")
print(f"X = {cx:.4f}")
print(f"Y = {cy:.4f}")
print(f"Z = {hover_z:.4f}")

print("")
print("Robot movement NOT executed.")
print("========================================")