# Task 등록 파일
# Isaac Sim이 실행에 시간이 많이 걸리므로 실행된 뒤에, 콜백으로 cartpole2_env1.py의 Cartpole2Env에서 CartpoleEnv를 import하도록 하기.
import sys
import gymnasium as gym # Isaac Sim과 함께 설치되어 push 환경 등을 생성하고 등록하는 패키지. Isaac Gym과는 무관함.

TASK_NAME = "Hawx-Cartpole-Push-Direct"

def register_Cartpole2Env():
    # Gym registry에 TASK_NAME라는 막대 미는 환경 등록
    #3. 등록만 하고 Cartpole2Env는 아직 import하지 않음.
    #2. 나중에 Isaac Sim이 실행되면 entry_point가 해석되면서 Cartpole2Env를 import하여 객체를 생성하게 됨.
    #1. Isaac Sim을 실행하고 external_callback으로 이 코드를 실행하는 커멘드
    '''
    ./isaaclab.sh play
        --rl_library rsl_rl
        --task Hawx-Cartpole-Push-Direct
        --checkpoint "$MODEL"
        --num_envs 1
        --viz kit
        --external_callback cartpol2_task1:register_Cartpole2Env
    '''

    if TASK_NAME not in gym.registry:
        gym.register(
            id=TASK_NAME,

            entry_point="isaaclab_tasks.core.cartpole.cartpole2_env1:Cartpole2Env",
            
            disable_env_checker=True,
            
            kwargs={
                "env_cfg_entry_point":
                    "isaaclab_tasks.core.cartpole.cartpole_direct_env_cfg:CartpoleEnvCfg",
                
                "rsl_rl_cfg_entry_point":
                    "isaaclab_tasks.core.cartpole.agents.rsl_rl_ppo_cfg:CartpoleDirectPPORunnerCfg",
                
                "default_agent": "rsl_rl",
            },
        )