from staking_sdk.v1.staking_client import TestnetStakingClient
from algosdk.mnemonic import to_private_key, to_public_key
from time import sleep
from json import load

with open("./NEEDED.json", 'r') as file:
    json = load(file)

MNEMONIC_MANAGER = json["MANAGER"]
MNEMONIC_DEPOSITOR = json["DEPOSITOR"]
ASA_ID = json["ASA_ID"]

POOL_DURATION = 60
POOL_REWARDS = 1000 #Base units
POOL_START = 0
DEPOSIT_AMOUNT = 100 #Base units

class Account:
    def __init__(self, mnenmonic: str) -> None:
        self.pk, self.address = to_private_key(mnenmonic), to_public_key(mnenmonic)

def main():
    #Create two account to interact
    manager = Account(MNEMONIC_MANAGER)
    depositor = Account(MNEMONIC_DEPOSITOR)

    #create the staking client on testnet
    client = TestnetStakingClient(user_address = manager.address)

    #Check the contract global and local state
    print("Pools number:", client.pools_number)
    print("Local State:")
    print(client.get_formatted_local_state(depositor.address), end="\n\n")

    #Do the app opt in if necessary
    try:
        client.submit_staking_app_opt_in(depositor.pk, depositor.address)
    except Exception as e:
        print(e)
    
    #Do the escrow opt in to ASA_ID if necessary
    try:
        client.submit_escrow_opt_in(ASA_ID, manager.pk, manager.address)
    except Exception as e:
        print(e)
    #Create a pool with the details inserted
    client.submit_create_pool(POOL_REWARDS, POOL_START, POOL_DURATION, ASA_ID, manager.pk)
    
    #Update the global state
    client.update_global_state()
    pool_id = client.get_latest_pool_created().id

    print("Pool {} created".format(pool_id))
    print(client.pools)

    #Deposit an amount in the last pool created
    client.submit_deposit_in_pool(pool_id, DEPOSIT_AMOUNT, depositor.pk, depositor.address)
    print("Deposited {} in the pool".format(DEPOSIT_AMOUNT))
    print("Local State:")
    print(client.get_formatted_local_state(depositor.address), end="\n\n")
    
    #Wait for the pool to end
    sleep(POOL_DURATION)

    #Claim from the pool 
    client.submit_claim_from_pool(pool_id, depositor.pk, depositor.address)
    print("Claimed from the pool {}".format(pool_id))
    print("Local State:")
    print(client.get_formatted_local_state(depositor.address), end="\n\n")

    #Delete the pool
    client.submit_delete_pool(pool_id, manager.pk)
    client.update_global_state()
    print("Pool {} deleted".format(pool_id))

    print("Pools number:", client.pools_number)
    print(client.pools)

if __name__ == "__main__":
    main()