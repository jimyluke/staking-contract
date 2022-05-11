from typing import List
from algosdk.future.transaction import SuggestedParams, AssetTransferTxn, ApplicationNoOpTxn, Transaction
from algosdk.logic import get_application_address
from ..utils import int_to_bytes
from ..contract_strings import StakingArguments

def create_pool(sender: str, params: SuggestedParams, staking_rewards: int, start_time: int, time_delta: int, staking_asa_id: int, staking_app_id) -> List[Transaction]:
    '''
        Returns a List of transaction without the group_id set rapresenting a pool creation group.
    '''
    args = [StakingArguments.create.encode(),
            int_to_bytes(int(start_time)),
            int_to_bytes(int(time_delta))]

    txns = [AssetTransferTxn(
                sender,
                params,
                get_application_address(staking_app_id),
                staking_rewards,
                staking_asa_id),
            ApplicationNoOpTxn(
                sender,
                params,
                staking_app_id,
                foreign_assets=[staking_asa_id],
                app_args=args)]
    
    return txns