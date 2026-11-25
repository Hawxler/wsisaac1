# 9번 뚜껑 집어 옮기기
import asyncio
import time
import traceback

import numpy as np
import omni.usd
import omni.timeline
import omni.physx
import omni.kit.app

from pxr import UsdPhysics, Sdf, Gf


# ============================================================
# Dobot Magician - Bottlecap9 Pick & Place
# Isaac Sim 6.1 / Script Editor
#
# 실행 시작: Pause (낙하 완료된 20-cap scene)
# 결과: 성공하면 Pause
#
# 관절 제어: 기존 angular drive
# 흡착: 기존 /PickSuctionJoint
# ============================================================

CAP_PATH = "/bottlecap9"
FIXED_JOINT_PATH = "/PickSuctionJoint"

SUCTION_LINK = (
    "/magician/Geometry/"
    "magician_root_link/"
    "magician_base_link/"
    "magician_link_1/"
    "magician_link_2/"
    "magician_link_3/"
    "magician_link_virtual/"
    "magician_link_4/"
    "magician_link_suction_cup"
)

JOINT_PATHS = [
    "/magician/Physics/magician_joint_1",
    "/magician/Physics/magician_joint_2",
    "/magician/Physics/magician_joint_3",
    "/magician/Physics/magician_joint_4",
]

# 9번 병뚜껑에서 이미 계산한 값
CAP_X = 0.2586
CAP_Y = -0.0255
CAP_TOP_Z = 0.0190

# 기존 성공한 suction 간격 약 6.75mm
PICK_GAP = 0.00675

HOVER_Z = CAP_TOP_Z + 0.030
PICK_Z = CAP_TOP_Z + PICK_GAP
LIFT_Z = CAP_TOP_Z + 0.075

# 주 관절 범위 (degree)
LIMITS = np.array([
    [-125.0, 125.0],
    [-5.0, 90.0],
    [-15.0, 70.0],
])

stage = omni.usd.get_context().get_stage()
timeline = omni.timeline.get_timeline_interface()
physx = omni.physx.get_physx_interface()
app = omni.kit.app.get_app()

drives = []
targets = np.array([0.0, 25.0, 26.0, 0.0])

for path in JOINT_PATHS:
    prim = stage.GetPrimAtPath(path)
    if not prim.IsValid():
        raise RuntimeError(f"Missing joint: {path}")
    drives.append(UsdPhysics.DriveAPI.Get(prim, "angular"))

fixed = UsdPhysics.FixedJoint.Get(stage, FIXED_JOINT_PATH)

if not fixed.GetPrim().IsValid():
    raise RuntimeError("PickSuctionJoint missing")

# 기존에 성공한 suction cup 쪽 anchor를 유지한다.
tip_local = np.array(
    fixed.GetLocalPos0Attr().Get(),
    dtype=float
)


# ------------------------------------------------------------
# Quaternion / PhysX pose
# ------------------------------------------------------------

def quat_rotate(q, v):
    xyz = np.asarray(q[:3], dtype=float)
    w = float(q[3])
    v = np.asarray(v, dtype=float)
    t = 2.0 * np.cross(xyz, v)
    return v + w * t + np.cross(xyz, t)


def quat_inverse(q):
    q = np.asarray(q, dtype=float)
    return np.array([-q[0], -q[1], -q[2], q[3]])


def quat_multiply(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b

    return np.array([
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ])


def body_pose(path):
    result = physx.get_rigidbody_transformation(path)

    if not result["ret_val"]:
        raise RuntimeError(f"PhysX body unavailable: {path}")

    return (
        np.array(result["position"], dtype=float),
        np.array(result["rotation"], dtype=float),
    )


def tool_tip():
    p, q = body_pose(SUCTION_LINK)
    return p + quat_rotate(q, tip_local)


# ------------------------------------------------------------
# Joint drive
# ------------------------------------------------------------

def command_joint(i, degree):
    targets[i] = float(degree)
    drives[i].GetTargetPositionAttr().Set(float(degree))


def command_pose(values):
    for i, value in enumerate(values):
        command_joint(i, value)


async def wait(seconds):
    end = time.perf_counter() + seconds

    while time.perf_counter() < end:
        if not timeline.is_playing():
            raise RuntimeError("Simulation stopped or paused")
        await app.next_update_async()


async def transition_pose(goal, label):
    print(f"\n[{label}]")

    start = targets.copy()
    goal = np.asarray(goal, dtype=float)

    steps = max(1, int(np.ceil(
        np.max(np.abs(goal - start)) / 5.0
    )))

    for i in range(1, steps + 1):
        q = start + (goal - start) * (i / steps)
        command_pose(q)
        await wait(0.40)

    await wait(0.50)


# ------------------------------------------------------------
# Numerical IK
#
# 실제 tool tip 위치를 이용하여
# J1, J2, J3의 작은 움직임을 보정한다.
# 별도의 Lula 설정 파일은 사용하지 않는다.
# ------------------------------------------------------------

async def estimate_jacobian():
    jac = np.zeros((3, 3))
    delta = 2.0

    for j in range(3):
        original = targets[j]

        trial = np.clip(
            original + delta,
            LIMITS[j, 0],
            LIMITS[j, 1],
        )

        if abs(trial - original) < 1.0:
            trial = original - delta

        command_joint(j, trial)
        await wait(0.45)
        p_trial = tool_tip()

        command_joint(j, original)
        await wait(0.45)
        p_base = tool_tip()

        jac[:, j] = (
            p_trial - p_base
        ) / (trial - original)

    return jac


async def reach_xyz(goal, label, tolerance=0.008):
    goal = np.asarray(goal, dtype=float)

    print(f"\n[{label}]")
    print("Target XYZ:", np.round(goal, 4))

    jac = None

    for iteration in range(18):
        current = tool_tip()
        error = goal - current
        distance = float(np.linalg.norm(error))

        print(
            f"  iteration={iteration:02d} "
            f"error={distance*1000:.1f} mm"
        )

        if distance < tolerance:
            print(f"[{label}] REACHED")
            return

        # 4회마다 실제 움직임으로 Jacobian 갱신
        if jac is None or iteration % 4 == 0:
            jac = await estimate_jacobian()
            current = tool_tip()
            error = goal - current

        damping = 0.001

        # Damped least-squares position correction
        jj = jac @ jac.T
        dq = jac.T @ np.linalg.solve(
            jj + (damping ** 2) * np.eye(3),
            error,
        )

        # 한 번에 너무 많이 움직이지 않는다.
        dq = np.clip(dq, -6.0, 6.0)

        previous = targets[:3].copy()
        next_q = np.clip(
            previous + dq,
            LIMITS[:, 0],
            LIMITS[:, 1],
        )

        actual_step = next_q - previous

        if np.linalg.norm(actual_step) < 0.05:
            raise RuntimeError(
                f"{label}: target unreachable at joint limit"
            )

        before = tool_tip()

        for j in range(3):
            command_joint(j, next_q[j])

        await wait(0.55)
        after = tool_tip()

        # 실제 이동량으로 Jacobian을 보정한다.
        observed = after - before
        predicted = jac @ actual_step
        denominator = float(actual_step @ actual_step)

        if denominator > 1e-8:
            jac = jac + np.outer(
                observed - predicted,
                actual_step
            ) / denominator

    remaining = np.linalg.norm(goal - tool_tip())

    if remaining > 0.012:
        raise RuntimeError(
            f"{label}: IK did not converge. "
            f"Remaining {remaining*1000:.1f} mm"
        )

    print(f"[{label}] REACHED (within 12 mm)")


# ------------------------------------------------------------
# Suction
# ------------------------------------------------------------

def suction_off():
    fixed.GetJointEnabledAttr().Set(False)
    print("[SUCTION] OFF")


def suction_on_cap9():
    """
    현재 PhysX pose로 양쪽 FixedJoint anchor를
    같은 월드 위치에 배치한다.
    기존 cap1의 localPos1을 재사용하지 않는다.
    """

    p0, q0 = body_pose(SUCTION_LINK)
    p1, q1 = body_pose(CAP_PATH)

    anchor_world = p0 + quat_rotate(q0, tip_local)

    local_p1 = quat_rotate(
        quat_inverse(q1),
        anchor_world - p1
    )

    local_q1 = quat_multiply(
        quat_inverse(q1), q0
    )

    fixed.GetBody1Rel().SetTargets([
        Sdf.Path(CAP_PATH)
    ])

    fixed.GetLocalPos0Attr().Set(
        Gf.Vec3f(*[float(v) for v in tip_local])
    )

    fixed.GetLocalPos1Attr().Set(
        Gf.Vec3f(*[float(v) for v in local_p1])
    )

    fixed.GetLocalRot0Attr().Set(
        Gf.Quatf(1.0, 0.0, 0.0, 0.0)
    )

    fixed.GetLocalRot1Attr().Set(
        Gf.Quatf(
            float(local_q1[3]),
            float(local_q1[0]),
            float(local_q1[1]),
            float(local_q1[2]),
        )
    )

    fixed.GetJointEnabledAttr().Set(True)

    print("[SUCTION] ON -> /bottlecap9")


# ============================================================
# Main
# ============================================================

async def main():
    try:
        print("\n===================================")
        print(" CAP9 PICK & PLACE START")
        print("===================================")

        # 기존 joint를 cap9에 연결하도록 준비
        suction_off()
        fixed.GetBody1Rel().SetTargets([
            Sdf.Path(CAP_PATH)
        ])

        # 현재 낙하 상태에서 Play 재개
        timeline.play()
        await wait(0.4)

        # 1. Ready
        await transition_pose(
            [0, 25, 26, 0],
            "READY"
        )

        # 2. Hover
        await reach_xyz(
            [CAP_X, CAP_Y, HOVER_Z],
            "HOVER"
        )

        # 3. Pick Approach
        await reach_xyz(
            [CAP_X, CAP_Y, PICK_Z],
            "PICK APPROACH",
            tolerance=0.006
        )

        # 너무 멀리 떨어진 채 흡착하지 않는다.
        distance = np.linalg.norm(
            tool_tip() -
            np.array([CAP_X, CAP_Y, PICK_Z])
        )

        if distance > 0.012:
            raise RuntimeError(
                "Suction tip is too far from cap9"
            )

        # 4. Suction ON
        cap_before, _ = body_pose(CAP_PATH)
        suction_on_cap9()
        await wait(0.5)

        # 5. Lift
        await reach_xyz(
            [CAP_X, CAP_Y, LIFT_Z],
            "LIFT"
        )

        cap_after, _ = body_pose(CAP_PATH)
        lift_distance = cap_after[2] - cap_before[2]

        print(
            f"[CAP9] Lift displacement = "
            f"{lift_distance*1000:.1f} mm"
        )

        if lift_distance < 0.020:
            raise RuntimeError(
                "Cap9 did not lift with the suction cup"
            )

        # 6. Transfer: 기존 성공한 Place 영역 사용
        await transition_pose(
            [targets[0], 25, 26, 0],
            "TRANSFER READY"
        )

        await transition_pose(
            [30, 25, 26, 0],
            "TRANSFER"
        )

        # 7. Lower
        await transition_pose(
            [30, 44, 26, 0],
            "LOWER"
        )

        # 8. Release
        suction_off()
        await wait(0.8)

        # 9. Retract
        await transition_pose(
            [30, 25, 26, 0],
            "RETRACT"
        )

        # 10. Return
        await transition_pose(
            [0, 25, 26, 0],
            "RETURN"
        )

        print("\n===================================")
        print(" CAP9 PICK & PLACE COMPLETE")
        print("===================================")

        timeline.pause()
        print("Simulation PAUSED")

    except Exception:
        print("\nCAP9 PICK & PLACE FAILED")
        traceback.print_exc()
        suction_off()
        timeline.pause()


asyncio.ensure_future(main())