from algosdk.v2client.algod import AlgodClient
from algosdk.mnemonic import to_private_key, to_public_key
from algosdk.future.transaction import  ApplicationCreateTxn, OnComplete, wait_for_confirmation, StateSchema
from staking_contract_pyteal import convert_to_teal, clear_state_program, approval_program, MAX_GLOBAL_BYTES, MAX_GLOBAL_INTS, MAX_LOCAL_BYTES, MAX_LOCAL_INTS
from base64 import b64decode
from json import load

with open("../NEEDED.json", 'r') as file:
    json = load(file)

MNEMONIC_CREATOR = json["CREATOR"]

class Account:
    def __init__(self, mnenmonic: str) -> None:
        self.pk, self.address = to_private_key(mnenmonic), to_public_key(mnenmonic)

def compile_program(client: AlgodClient, source_code):
    compile_response = client.compile(source_code)
    return b64decode(compile_response['result'])

def state_schema(ints: int, bytes: int) -> StateSchema:
    return StateSchema(ints,bytes)

def create_application(algod_client: AlgodClient, private_key, creator, approval_program, clear_program, global_schema, local_schema):
    on_complete = OnComplete.NoOpOC.real

    params = algod_client.suggested_params()

    txn = ApplicationCreateTxn(creator, params, on_complete, approval_program, clear_program, global_schema, local_schema)

    txid = algod_client.send_transaction(txn.sign(private_key))
    
    wait_for_confirmation(algod_client, txid, 5)

    transaction_response = algod_client.pending_transaction_info(txid)

    return transaction_response['application-index']

def main():
    creator = Account(MNEMONIC_CREATOR)
    algod_client = AlgodClient("", "https://node.testnet.algoexplorerapi.io", headers={"User-Agent": "algosdk"})
    
    global_schema = state_schema(MAX_GLOBAL_INTS, MAX_GLOBAL_BYTES)
    local_schema = state_schema(MAX_LOCAL_INTS, MAX_LOCAL_BYTES)
    
    convert_to_teal()
    
    # compile approval program to binary
    approval_program_compiled = compile_program(algod_client, approval_program())
    # compile clear state program to binary
    clear_state_program_compiled = compile_program(algod_client, clear_state_program())
    
    # create new application
    app_id = create_application(algod_client, creator.pk, creator.address, approval_program_compiled, clear_state_program_compiled, global_schema, local_schema)

    print("APPLICATION CREATED")
    print("app id: {}".format(app_id))

if __name__ == "__main__":
    main()