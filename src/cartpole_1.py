# 막대를 일정한 주기로 밀어주는 환경을 구현한 코드입니다. 기존 CartpoleEnv를 상속받아 _pre_physics_step 메서드를 오버라이드하여 일정 step마다 push action을 수행하도록 합니다.
import sys
import gymnasium as gym

from isaaclab_tasks.core.cartpole.cartpole_direct_env import CartpoleEnv
from isaaclab_rl.entrypoints import run_play_cli


# ---------------------------------------------------------
# 기존 Cartpole을 상속받아 외부 힘만 추가
# ---------------------------------------------------------
class PushCartpoleEnv(CartpoleEnv):

    def __init__(self, cfg, render_mode=None, **kwargs):
        super().__init__(cfg, render_mode, **kwargs)
        self.push_step = 0

    def _pre_physics_step(self, actions):

        # PPO가 계산한 원래 제어 힘
        super()._pre_physics_step(actions)

        self.push_step += 1
        phase = self.push_step % 300

        # 오른쪽으로 +60 N 외란
        if 60 <= phase < 72:
            self.actions[:, 0] += 60.0

        # 왼쪽으로 -60 N 외란
        elif 180 <= phase < 192:
            self.actions[:, 0] -= 60.0


# ---------------------------------------------------------
# 기존 Isaac-Cartpole-Direct는 건드리지 않고
# 새로운 task 이름으로 등록
# ---------------------------------------------------------
TASK_NAME = "Hawx-Cartpole-Push-Direct"

if TASK_NAME not in gym.registry:
    gym.register(
        id=TASK_NAME,
        entry_point=PushCartpoleEnv,
        disable_env_checker=True,
        kwargs={
            "env_cfg_entry_point":
                "isaaclab_tasks.core.cartpole.cartpole_direct_env_cfg:CartpoleEnvCfg",

            "rsl_rl_cfg_entry_point":
                "isaaclab_tasks.core.cartpole.agents.rsl_rl_ppo_cfg:CartpoleDirectPPORunnerCfg",

            "default_agent": "rsl_rl",
        },
    )


# ---------------------------------------------------------
# checkpoint
# ---------------------------------------------------------
if len(sys.argv) < 2:
    raise RuntimeError("checkpoint 경로가 필요합니다.")

checkpoint = sys.argv[1]


# ---------------------------------------------------------
# 학습된 PPO policy 실행
# ---------------------------------------------------------
run_play_cli([
    "--rl_library", "rsl_rl",
    "--task", TASK_NAME,
    "--checkpoint", checkpoint,
    "--num_envs", "1",
    "--viz", "kit",
    "--real-time",
    "physics=isaacsim_physx",
])