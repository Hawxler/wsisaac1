# 병뚜껑 20개 옮기기
import random

import omni.usd
import omni.kit.commands
from pxr import Gf


# ============================================================
# Create 20 randomly positioned bottle caps
# 실행: Isaac Sim Script Editor
# 상태: Stop
# ============================================================

stage = omni.usd.get_context().get_stage()

SOURCE = "/bottlecap1"
COUNT = 20

# 원본 병뚜껑 주변에 모이도록 분산
XY_RANGE = 0.035  # ±35 mm

# 공중에서 순서대로 떨어뜨려 쌓기 위한 시작 높이
BASE_HEIGHT = 0.05
HEIGHT_STEP = 0.025

random.seed(42)

source = stage.GetPrimAtPath(SOURCE)

if not source.IsValid():
    raise RuntimeError("Source /bottlecap1 not found")

# 원본 병뚜껑 위치
translate = source.GetAttribute("xformOp:translate")

if not translate.IsValid():
    raise RuntimeError("Source translate attribute not found")

origin = translate.Get()

# 기존 suction 연결은 OFF
suction = stage.GetPrimAtPath("/PickSuctionJoint")

if suction.IsValid():
    enabled = suction.GetAttribute("physics:jointEnabled")
    if enabled.IsValid():
        enabled.Set(False)

# 이전 실행으로 만들어진 복제본 삭제
for i in range(2, COUNT + 1):
    path = f"/bottlecap{i}"
    if stage.GetPrimAtPath(path).IsValid():
        stage.RemovePrim(path)

# 원본 병뚜껑도 더미에 포함
paths = [SOURCE]

for i in range(2, COUNT + 1):

    target = f"/bottlecap{i}"

    success, _ = omni.kit.commands.execute(
        "CopyPrim",
        path_from=SOURCE,
        path_to=target,
    )

    if not success:
        raise RuntimeError(f"Copy failed: {target}")

    paths.append(target)

# 위치 무작위 배치
random.shuffle(paths)

for index, path in enumerate(paths):

    prim = stage.GetPrimAtPath(path)
    pos_attr = prim.GetAttribute("xformOp:translate")

    dx = random.uniform(-XY_RANGE, XY_RANGE)
    dy = random.uniform(-XY_RANGE, XY_RANGE)

    z = BASE_HEIGHT + index * HEIGHT_STEP

    pos_attr.Set(
        Gf.Vec3d(
            float(origin[0]) + dx,
            float(origin[1]) + dy,
            z,
        )
    )

    print(
        f"{path}: "
        f"x={float(origin[0])+dx:.3f}, "
        f"y={float(origin[1])+dy:.3f}, "
        f"z={z:.3f}"
    )

print("")
print(f"CREATED {len(paths)} BOTTLE CAPS")
print("Press Play to drop the caps.")