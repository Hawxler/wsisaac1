# 병뚜껑 20개의 현재 좌표/회전 읽기
import omni.usd
import omni.physx
import omni.timeline

# Current Isaac Sim stage
stage = omni.usd.get_context().get_stage()
timeline = omni.timeline.get_timeline_interface()

# PhysX simulation interface
physx = omni.physx.get_physx_interface()

if timeline.is_stopped():
    raise RuntimeError(
        "Simulation is stopped. "
        "Use Play, then Pause before reading positions."
    )

cap_poses = {}

print("====================================")
print("CURRENT BOTTLE CAP WORLD POSES")
print("====================================")

for i in range(1, 21):
    path = f"/bottlecap{i}"

    prim = stage.GetPrimAtPath(path)

    if not prim.IsValid():
        print(f"{path}: NOT FOUND")
        continue

    # Read current physics transform, not initial USD pose
    result = physx.get_rigidbody_transformation(path)

    if not result["ret_val"]:
        print(f"{path}: PHYSX POSE NOT AVAILABLE")
        continue

    p = result["position"]
    q = result["rotation"]  # x, y, z, w

    x = float(p[0])
    y = float(p[1])
    z = float(p[2])

    cap_poses[path] = {
        "position": (x, y, z),
        "rotation_xyzw": tuple(float(v) for v in q),
    }

    print(
        f"{path:14s} "
        f"X={x:+.4f}  "
        f"Y={y:+.4f}  "
        f"Z={z:+.4f} m"
    )

print("====================================")
print(f"CAP POSES READ: {len(cap_poses)} / 20")
print("====================================")