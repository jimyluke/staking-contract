from algosdk.future.transaction import ApplicationCloseOutTxn, Transaction, SuggestedParams

def staking_app_close_out(sender: str, params: SuggestedParams, app_id: int) -> Transaction:
    return ApplicationCloseOutTxn(sender, params, app_id)
    