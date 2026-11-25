# Isaac Sim > Window > Script Editor에서 실행
import asyncio
import time

import omni.usd
import omni.timeline
import omni.kit.app
from pxr import UsdPhysics


# ============================================================
# Dobot Magician - 1 Bottle Cap Pick & Place
#
# 실행 위치:
#   Isaac Sim -> Window -> Script Editor
#
# 실행 전 상태:
#   dobot_pick_place_1cap.usd 열기
#   Simulation = Play
#
# 중요:
#   mimic_1 / mimic_2는 직접 제어하지 않는다.
# ============================================================


# ------------------------------------------------------------
# Prim paths
# ------------------------------------------------------------

JOINT_PATHS = {
    "J1": "/magician/Physics/magician_joint_1",
    "J2": "/magician/Physics/magician_joint_2",
    "J3": "/magician/Physics/magician_joint_3",
    "J4": "/magician/Physics/magician_joint_4",
}

SUCTION_JOINT_PATH = "/PickSuctionJoint"


# ------------------------------------------------------------
# Timing
# ------------------------------------------------------------

# 각 작은 관절 이동 후 기다리는 시간
MOVE_WAIT = 1.0

# suction ON 후 기다리는 시간
SUCTION_ON_WAIT = 0.5

# suction OFF 후 병뚜껑이 바닥에 안정될 시간
SUCTION_OFF_WAIT = 0.8


stage = omni.usd.get_context().get_stage()
timeline = omni.timeline.get_timeline_interface()
app = omni.kit.app.get_app()


# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def require_prim(path):
    prim = stage.GetPrimAtPath(path)

    if not prim.IsValid():
        raise RuntimeError(f"Prim not found: {path}")

    return prim


def get_drive(joint_name):
    path = JOINT_PATHS[joint_name]
    prim = require_prim(path)

    # 기존 angular drive를 그대로 사용한다.
    drive = UsdPhysics.DriveAPI.Apply(prim, "angular")

    return drive


drives = {
    "J1": get_drive("J1"),
    "J2": get_drive("J2"),
    "J3": get_drive("J3"),
    "J4": get_drive("J4"),
}


suction_prim = require_prim(SUCTION_JOINT_PATH)
suction_joint = UsdPhysics.FixedJoint.Get(stage, SUCTION_JOINT_PATH)

if not suction_joint.GetPrim().IsValid():
    raise RuntimeError("/PickSuctionJoint is not a valid FixedJoint")


def set_joint(joint_name, degree):
    """Joint Inspector의 Target Position과 같은 angular drive target을 설정한다."""

    drive = drives[joint_name]

    attr = drive.GetTargetPositionAttr()

    if not attr:
        attr = drive.CreateTargetPositionAttr()

    attr.Set(float(degree))


def set_pose(j1, j2, j3, j4):
    """4개의 active joint target을 한 번에 설정한다."""

    set_joint("J1", j1)
    set_joint("J2", j2)
    set_joint("J3", j3)
    set_joint("J4", j4)


def set_suction(enabled):
    """PhysicsFixedJoint의 Joint Enabled를 ON/OFF한다."""

    attr = suction_joint.GetJointEnabledAttr()

    if not attr:
        attr = suction_joint.CreateJointEnabledAttr()

    attr.Set(bool(enabled))

    if enabled:
        print("[SUCTION] ON")
    else:
        print("[SUCTION] OFF")


async def wait_seconds(seconds):
    """
    time.sleep()을 사용하지 않는다.
    Isaac Sim frame/physics가 계속 진행되도록
    next_update_async()를 사용하며 기다린다.
    """

    end_time = time.perf_counter() + seconds

    while time.perf_counter() < end_time:
        await app.next_update_async()


async def move_j2_sequence(values, label):
    print(f"\n--- {label} ---")

    for value in values:
        set_joint("J2", value)

        print(
            f"{label}: "
            f"J2 -> {value:.1f} deg"
        )

        await wait_seconds(MOVE_WAIT)


async def move_j1_sequence(values, label):
    print(f"\n--- {label} ---")

    for value in values:
        set_joint("J1", value)

        print(
            f"{label}: "
            f"J1 -> {value:.1f} deg"
        )

        await wait_seconds(MOVE_WAIT)


# ============================================================
# Main sequence
# ============================================================

async def pick_place_one_cap():

    try:

        print("")
        print("==========================================")
        print(" DOBOT 1-CAP PICK & PLACE START")
        print("==========================================")

        # ----------------------------------------------------
        # Simulation 확인
        # ----------------------------------------------------

        if not timeline.is_playing():
            raise RuntimeError(
                "Simulation is not playing. "
                "Click Play in Isaac Sim first."
            )

        # 혹시 이전 상태가 남아 있어도 시작 시 suction OFF
        set_suction(False)

        await wait_seconds(0.3)


        # ====================================================
        # 1. 시작 자세
        # ====================================================

        print("\n--- READY ---")
        print("J1=0, J2=25, J3=26, J4=0")

        set_pose(
            j1=0,
            j2=25,
            j3=26,
            j4=0,
        )

        await wait_seconds(1.0)


        # ====================================================
        # 2. Pick 자세로 내려가기
        #
        # 검증된 Pick:
        # J1=0
        # J2=44
        # J3=26
        # J4=0
        # ====================================================

        await move_j2_sequence(
            [30, 35, 40, 44],
            "PICK APPROACH"
        )


        # ====================================================
        # 3. Suction ON
        # ====================================================

        print("\n--- PICK ---")

        set_suction(True)

        await wait_seconds(SUCTION_ON_WAIT)


        # ====================================================
        # 4. Lift
        #
        # 44 -> 40 -> 35 -> 30 -> 25
        # ====================================================

        await move_j2_sequence(
            [40, 35, 30, 25],
            "LIFT"
        )


        # ====================================================
        # 5. Transfer
        #
        # J1:
        # 0 -> 10 -> 20 -> 30
        # ====================================================

        await move_j1_sequence(
            [10, 20, 30],
            "TRANSFER"
        )


        # ====================================================
        # 6. Lower
        #
        # J2:
        # 25 -> 30 -> 35 -> 40 -> 44
        # ====================================================

        await move_j2_sequence(
            [30, 35, 40, 44],
            "LOWER"
        )


        # ====================================================
        # 7. Suction OFF
        # ====================================================

        print("\n--- RELEASE ---")

        set_suction(False)

        await wait_seconds(SUCTION_OFF_WAIT)


        # ====================================================
        # 8. Retract
        #
        # J2:
        # 44 -> 35 -> 30 -> 25
        # ====================================================

        await move_j2_sequence(
            [35, 30, 25],
            "RETRACT"
        )


        # ====================================================
        # 9. Return
        #
        # J1:
        # 30 -> 20 -> 10 -> 0
        # ====================================================

        await move_j1_sequence(
            [20, 10, 0],
            "RETURN"
        )


        # 최종 자세를 확실하게 지정
        set_pose(
            j1=0,
            j2=25,
            j3=26,
            j4=0,
        )

        await wait_seconds(1.0)


        # ====================================================
        # 완료
        # ====================================================

        print("")
        print("==========================================")
        print(" PICK & PLACE COMPLETE")
        print(" Final pose: J1=0, J2=25, J3=26, J4=0")
        print(" Suction: OFF")
        print("==========================================")

        # Stop하면 병뚜껑이 초기 상태로 되돌아가므로
        # 최종 결과를 눈으로 확인할 수 있도록 Pause한다.
        timeline.pause()

        print("Simulation PAUSED for inspection.")


    except Exception as e:

        print("")
        print("==========================================")
        print(" PICK & PLACE ERROR")
        print("==========================================")
        print(repr(e))

        timeline.pause()


# Script Editor에서 실행했을 때
# UI/physics frame을 막지 않고 비동기로 동작시킨다.
asyncio.ensure_future(pick_place_one_cap())