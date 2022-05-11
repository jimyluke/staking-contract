from typing import List
from algosdk.future.transaction import SuggestedParams, AssetTransferTxn, ApplicationNoOpTxn, Transaction
from algosdk.logic import get_application_address
from ..utils import int_to_bytes
from ..contract_strings import StakingArguments

def deposit(sender: str, params: SuggestedParams, amount: int, staking_asa_id: int, staking_app_id: int, pool_id: int) -> List[Transaction]:
    '''
        Returns a List of transaction without the group_id set rapresenting a deposit group.
    '''
    args = [StakingArguments.deposit.encode(),
            int_to_bytes(pool_id)]

    txns = [AssetTransferTxn(
                sender,
                params,
                get_application_address(staking_app_id),
                amount,
                staking_asa_id),
            ApplicationNoOpTxn(
                sender,
                params,
                staking_app_id,
                foreign_assets=[staking_asa_id],
                app_args=args)]

    return txns