from typing import Dict, TypedDict

class UserStakedState(TypedDict):
    POOL_ID: int
    user_staked: int
    user_score: int
    STAKING_ASA_ID: int
