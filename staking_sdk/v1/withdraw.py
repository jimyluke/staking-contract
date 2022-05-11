from algosdk.future.transaction import SuggestedParams, ApplicationNoOpTxn, Transaction
from ..utils import int_to_bytes
from ..contract_strings import StakingArguments

def withdraw(sender: str, params: SuggestedParams, staking_asa_id: int, staking_app_id: int, pool_id: int) -> Transaction:
    '''
        Returns a transaction without rapresenting a withdraw.
    '''  
    args = [StakingArguments.withdraw.encode(),
            int_to_bytes(pool_id)]

    txn = ApplicationNoOpTxn(
                sender,
                params,
                staking_app_id,
                foreign_assets=[staking_asa_id],
                app_args=args)

    return txn