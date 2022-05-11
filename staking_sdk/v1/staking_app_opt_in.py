from algosdk.future.transaction import ApplicationOptInTxn, Transaction, SuggestedParams

def staking_app_opt_in(sender: str, params: SuggestedParams, app_id: int) -> Transaction:
    return ApplicationOptInTxn(sender, params, app_id)