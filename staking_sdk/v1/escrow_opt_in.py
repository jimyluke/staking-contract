from typing import List
from algosdk.future.transaction import SuggestedParams, PaymentTxn, ApplicationNoOpTxn, Transaction
from algosdk.logic import get_application_address
from ..contract_strings import StakingArguments

def escrow_opt_in(sender: str, params: SuggestedParams, staking_asa_id: int, staking_app_id: int) -> List[Transaction]:
    '''
        Returns a List of transaction without the group_id set rapresenting a escrow_opt_in group.
    '''

    args = [StakingArguments.optin.encode()]

    txns = [PaymentTxn(
                sender,
                params,
                get_application_address(staking_app_id),
                101000),
            ApplicationNoOpTxn(
                sender,
                params,
                staking_app_id,
                foreign_assets=[staking_asa_id],
                app_args=args)]
    
    return txns