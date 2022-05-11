from pyteal import *

#Running this script will create a teal source for approval and clear state program
#hardcoding in it the MANAGER_ADDRESS and the MAX_SECONDS_TO_CLAIM that must be set.

#EDIT THIS AS WANTED
MANAGER_ADDRESS = ""
MAX_SECONDS_TO_CLAIM = int(60*60*24*365) #One year


#DO NOT EDIT
TX_FEE = 1000
MIN_AMOUNT_PER_ASA = 100000
MAX_LOCAL_INTS = 0
MAX_LOCAL_BYTES = 4
MAX_GLOBAL_INTS = 0
MAX_GLOBAL_BYTES = 64

@Subroutine(TealType.uint64)
def isOptedInAsset(addr, id):
    balance = AssetHolding.balance(addr,id)
    return Seq([
        balance,
        balance.hasValue()
    ])

#This subroutine will be necessary only if the overflow check is uncommented.
#Please read the NOTES in the doc for further information
#@Subroutine(TealType.uint64)
#def totalSupply(id):
#    total = AssetParam.total(id)
#    return Seq([ 
#            total,
#            Assert(total.hasValue()),
#            total.value()
#        ])

@Subroutine(TealType.none)
def searchPoolId(pool_id, account):
    '''If the pool_id is not found in the depositor's local state saves in scratch variable 'i' the uint 0, 
       if is found saves in scratch variable 'i' the uint of the index (from 1 to MAX_LOCAL_BYTES)'''

    return Seq([
        i.store(Int(1)),
        While(i.load() < Int(MAX_LOCAL_BYTES + 1))
        .Do(   
            Seq([
                If(hasLocalKey(account, Itob(i.load())))
                .Then(
                    If(Extract(App.localGet(account,Itob(i.load())),Int(0),Int(8)) == pool_id)
                    .Then(
                        Return()
                    )
                ),
                i.store(i.load() + Int(1))
            ])
        ),
        i.store(Int(0)),
        Return()
    ])

@Subroutine(TealType.none)
def findFirstFree(account):
    '''Finds the first index free in the local state of the account. Saves in the scratch variable i the index of the first key free to write (i.e. not alredy deposited)
       Saves 0 if the local state is full (i.e. the account has alredy deposited in MAX_LOCAL_BYTES pools'''

    return Seq([
        i.store(Int(1)),
        While(i.load() < Int(MAX_LOCAL_BYTES + 1))
        .Do(   
            Seq([
                If(Not(hasLocalKey(account, Itob(i.load()))))
                .Then(
                    Return()
                ),
                i.store(i.load() + Int(1))
            ])
        ),
        i.store(Int(0)),
        Return()
    ])


@Subroutine(TealType.uint64)
def hasLocalKey(account, key):
    key: MaybeValue = App.localGetEx(account,Global.current_application_id(),key)
    return Seq([
        key,
        key.hasValue()
    ])

@Subroutine(TealType.uint64)
def hasGlobalKey(key, app_id):
    key: MaybeValue = App.globalGetEx(app_id,key)
    return Seq([
        key,
        key.hasValue()
    ])

def ExtractUint64FromGlobalKey(key, start):
    return ExtractUint64(
                App.globalGet(key),
                start
            )

def ExtractBytesFromGlobalKey(key, start, lenght):
    return Extract(
                App.globalGet(key),
                start,
                lenght
            )

def ExtractUint64FromLocalKey(account, key, start):
    return ExtractUint64(
                App.localGet(account, key),
                start
            )

def ExtractBytesFromLocalKey(account, key, start, lenght):
    return Extract(
                App.localGet(account, key),
                start,
                lenght
            )

rewards = ScratchVar(TealType.uint64,0)
relative_time = ScratchVar(TealType.uint64,1)
i = ScratchVar(TealType.uint64, 2)
pool_id = ScratchVar(TealType.bytes, 3)
time_delta = ScratchVar(TealType.uint64, 4)

MG = ExtractBytesFromGlobalKey(Bytes("INFO"), Int(0), Int(32))
POOL_NUM = ExtractUint64FromGlobalKey(Bytes("INFO"), Int(32))
TR = lambda key: ExtractUint64FromGlobalKey(key,Int(0))
UN = lambda key: ExtractUint64FromGlobalKey(key,Int(8))
TBC = lambda key: ExtractUint64FromGlobalKey(key,Int(16))
TS = lambda key: ExtractUint64FromGlobalKey(key,Int(24))
TSC = lambda key: ExtractUint64FromGlobalKey(key,Int(32))
ST = lambda key: ExtractUint64FromGlobalKey(key,Int(40))
TD = lambda key: ExtractUint64FromGlobalKey(key,Int(48))
CID_G = lambda key : ExtractUint64FromGlobalKey(key,Int(56))

UST = lambda key: ExtractUint64FromLocalKey(Txn.sender(),key,Int(8))
USC = lambda key: ExtractUint64FromLocalKey(Txn.sender(),key,Int(16))
CID_L = lambda key: ExtractUint64FromLocalKey(Txn.sender(),key,Int(24))

def approval_program(manager: str = MANAGER_ADDRESS):
    on_creation = Seq([
        App.globalPut(Bytes("INFO"), Concat(Addr(manager),Itob(Int(0)))),

        Approve()
    ])

    opt_in_asset = Seq([
        Assert(
            And(
                Global.group_size() == Int(2),
                Txn.assets.length() == Int(1),
                Gtxn[0].type_enum() == TxnType.Payment,
                Gtxn[0].amount() == Int(MIN_AMOUNT_PER_ASA + TX_FEE),
                Gtxn[0].receiver() == Global.current_application_address(),
                Gtxn[0].rekey_to() == Global.zero_address(),
                Gtxn[0].close_remainder_to() == Global.zero_address(),
                Gtxn[0].sender() == MG,
                Gtxn[1].type_enum() == TxnType.ApplicationCall,
                Gtxn[1].sender() == Gtxn[0].sender(),
                Gtxn[1].rekey_to() == Global.zero_address(),
                Not(isOptedInAsset(Global.current_application_address(), Txn.assets[0]))
            )
        ),
        
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.asset_amount: Int(0),
                TxnField.fee: Int(TX_FEE),
                TxnField.xfer_asset: Txn.assets[0],
                TxnField.asset_receiver: Global.current_application_address()
            }
        ),
        InnerTxnBuilder.Submit(),
        
        Approve()
    ])

    handle_optin = Approve()

    handle_closeout = Seq([
        Assert(And(
            Global.group_size() == Int(1),
            Txn.rekey_to() == Global.zero_address(),
        )),

        i.store(Int(1)),

        While(i.load() < Int(MAX_LOCAL_BYTES + 1))
        .Do(
            Seq([
                If(hasLocalKey(Txn.sender(), Itob(i.load())))
                .Then(
                    Reject()
                ),
                i.store(i.load() + Int(1))
            ])
        ),

        Approve()
    ])
    
    handle_updateapp = Reject()

    handle_deleteapp = Reject()  

    on_pool_create = Seq([
        Assert(
            And(
                Txn.assets.length() == Int(1),
                isOptedInAsset(Global.current_application_address(), Txn.assets[0]),
                Txn.accounts.length() == Int(0),
                Global.group_size() == Int(2),
                Txn.sender() == MG,                                                                     #Is Manager address
                #Len(BytesMul(Txn.application_args[2], Itob(totalSupply(Txn.assets[0])))) <= Int(8),    #Upper limit for time delta to avoid overflow (Time Delta * Total Supply < 2**64 - 1), possible to remove but a user can get an error while depositing very big amounts. When uncommenting this check also the TotalSupply subroutine must be uncommented
                Gtxn[0].type_enum() == TxnType.AssetTransfer,
                Gtxn[0].asset_receiver() == Global.current_application_address(),
                Gtxn[0].xfer_asset() == Txn.assets[0],
                Gtxn[0].asset_amount() != Int(0),
                Gtxn[0].rekey_to() == Global.zero_address(),
                Gtxn[0].asset_close_to() == Global.zero_address(),
                Gtxn[1].type_enum() == TxnType.ApplicationCall,
                Gtxn[1].rekey_to() == Global.zero_address(),
                Gtxn[0].sender() == Gtxn[1].sender(),
                Not(hasGlobalKey(Itob(Global.latest_timestamp()),Global.current_application_id()))
            )
        ),
        time_delta.store(Btoi(Txn.application_args[1])),

        If(time_delta.load() < Global.latest_timestamp())
        .Then(
            time_delta.store(Global.latest_timestamp())
        ),

        App.globalPut(
            Itob(Global.latest_timestamp()),    #creation timestamp used as logic id
            Concat(
                Itob(Gtxn[0].asset_amount()),   #Total Rewards (TR)
                Itob(Int(0)),                   #Number of users (UN)
                Itob(Gtxn[0].asset_amount()),   #To be claimed (TBC), after claims decreases
                Itob(Int(0)),                   #Total Staked (TS)
                Itob(Int(0)),                   #Total Score (TSC)
                Itob(time_delta.load()),        #Start time (ST)
                Txn.application_args[2],        #Time delta (TD)
                Itob(Txn.assets[0])             #Currency id (CID_G)
            )
        ),

        App.globalPut(
            Bytes("INFO"),
            Concat(
                ExtractBytesFromGlobalKey(Bytes("INFO"), Int(0), Int(32)),
                Itob(POOL_NUM + Int(1))
            )
        ),

        Approve()
    ])
    

    on_deposit = Seq([
        Assert(
            And(
                Txn.assets.length() == Int(1),
                Txn.accounts.length() == Int(0),
                Global.group_size() == Int(2),
                Gtxn[0].type_enum() == TxnType.AssetTransfer,
                Gtxn[0].asset_receiver() == Global.current_application_address(),
                Gtxn[0].xfer_asset() == Txn.assets[0],
                Gtxn[0].asset_amount() != Int(0),
                Gtxn[0].rekey_to() == Global.zero_address(),
                Gtxn[0].asset_close_to() == Global.zero_address(),
                Gtxn[1].type_enum() == TxnType.ApplicationCall,
                Gtxn[1].rekey_to() == Global.zero_address(),
                Gtxn[0].sender() == Gtxn[1].sender(),
                hasGlobalKey(Txn.application_args[1],Global.current_application_id()),                  #Pool Is created
                Txn.assets[0] == CID_G(Txn.application_args[1]),                                        #Is the right pool for the asset
                Global.latest_timestamp() < ST(Txn.application_args[1]) + TD(Txn.application_args[1])   #Pool is not ended
            )
        ),

        If(Global.latest_timestamp() <= ST(Txn.application_args[1]))
        .Then(
            relative_time.store(
                TD(Txn.application_args[1])
            )
        )
        .Else(
            relative_time.store(
                TD(Txn.application_args[1]) + ST(Txn.application_args[1]) - Global.latest_timestamp()
            )
        ),

        searchPoolId(Txn.application_args[1], Txn.sender()),

        If(i.load() != Int(0)) #if the depositor has alredy deposited, he has alredy been counted
        .Then(
            Seq([
                #Update depositor local state
                App.localPut(
                    Txn.sender(),
                    Itob(i.load()),
                    Concat(
                        Txn.application_args[1],                                                        #Pool_id
                        Itob(UST(Itob(i.load())) + Gtxn[0].asset_amount()),                             #UST(k-1) + UST(k)
                        Itob(USC(Itob(i.load())) + Mul(relative_time.load(),Gtxn[0].asset_amount())),   #USC(k-1) + USC(k)
                        Itob(Txn.assets[0])                                                             #CID_L
                    )
                ),

                #Update global state
                App.globalPut(
                    Txn.application_args[1],
                    Concat(
                        ExtractBytesFromGlobalKey(Txn.application_args[1], Int(0), Int(24)),
                        Itob(TS(Txn.application_args[1]) + Gtxn[0].asset_amount()),                             #TS(k-1) + TS(k)
                        Itob(TSC(Txn.application_args[1]) + Mul(relative_time.load(),Gtxn[0].asset_amount())),  #TSC(k-1) + TSC(k)
                        ExtractBytesFromGlobalKey(Txn.application_args[1], Int(40), Int(24)),
                    )
                )
            ])
        )
        .Else(
            Seq([
                findFirstFree(Txn.sender()),

                If(i.load() == Int(0))
                .Then(
                    Reject()
                ),

                App.localPut(
                    Txn.sender(),
                    Itob(i.load()),
                    Concat(
                        Txn.application_args[1],                                #Pool_id
                        Itob(Gtxn[0].asset_amount()),                           #UST(k-1) + UST(k)
                        Itob(Mul(relative_time.load(),Gtxn[0].asset_amount())), #USC(k-1) + USC(k)
                        Itob(Txn.assets[0])                                     #CID_L
                    )
                ),

                App.globalPut(
                    Txn.application_args[1],
                    Concat(
                        ExtractBytesFromGlobalKey(Txn.application_args[1], Int(0), Int(8)),
                        Itob(UN(Txn.application_args[1]) + Int(1)),                                             #Increment the total users
                        ExtractBytesFromGlobalKey(Txn.application_args[1], Int(16), Int(8)),
                        Itob(TS(Txn.application_args[1]) + Gtxn[0].asset_amount()),                             #TS(K-1) + TS(k)
                        Itob(TSC(Txn.application_args[1]) + Mul(relative_time.load(),Gtxn[0].asset_amount())),  #TSC(K-1) + TSC(k)
                        ExtractBytesFromGlobalKey(Txn.application_args[1], Int(40), Int(24)),
                    )
                )
            ])
        ),

        Approve()
    ])

    on_claim = Seq([
        searchPoolId(Txn.application_args[1], Txn.sender()),

        Assert(
            And(
                Txn.assets.length() == Int(1),
                Txn.accounts.length() == Int(0),
                Global.group_size() == Int(1),
                Txn.type_enum() == TxnType.ApplicationCall,
                Txn.fee() == Int(2*TX_FEE),
                Txn.rekey_to() == Global.zero_address(),
                hasGlobalKey(Txn.application_args[1], Global.current_application_id()),                  #Pool is created
                i.load() != Int(0),                                                                     #Address has deposited
                Txn.assets[0] == CID_G(Txn.application_args[1]),                                        #Is the right pool for the asset
                Global.latest_timestamp() > ST(Txn.application_args[1]) + TD(Txn.application_args[1]),  #Check that the pool is ended
            )
        ),
        
        rewards.store(
            WideRatio(
                [TR(Txn.application_args[1]), USC(Itob(i.load()))],
                [TSC(Txn.application_args[1])]
            )
        ),

        If(TBC(Txn.application_args[1]) < rewards.load())
        .Then(
            rewards.store(
                TBC(Txn.application_args[1])
            )
        ),

        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.asset_amount: UST(Itob(i.load())) + rewards.load(),
                TxnField.fee: Int(0),
                TxnField.xfer_asset: Txn.assets[0],
                TxnField.asset_receiver: Txn.sender()
            }
        ),
        InnerTxnBuilder.Submit(),

        App.localDel(Txn.sender(), Itob(i.load())),

        App.globalPut(
            Txn.application_args[1],
            Concat(
                ExtractBytesFromGlobalKey(Txn.application_args[1], Int(0), Int(8)),
                Itob(UN(Txn.application_args[1]) - Int(1)),                             #Decrement the total users
                Itob(TBC(Txn.application_args[1]) - rewards.load()),                    #Decrement the amount to be claimed
                ExtractBytesFromGlobalKey(Txn.application_args[1], Int(24), Int(40)),
            )
        ),

        Approve()
    ])

    on_withdrawal = Seq([
        searchPoolId(Txn.application_args[1], Txn.sender()),

        Assert(
            And(
                Txn.assets.length() == Int(1),
                Txn.accounts.length() == Int(0),
                Global.group_size() == Int(1),
                Txn.type_enum() == TxnType.ApplicationCall,
                Txn.fee() == Int(2*TX_FEE),
                Txn.rekey_to() == Global.zero_address(),
                Not(hasGlobalKey(Txn.application_args[1],Global.current_application_id())), #The pool has been deleted
                i.load() != Int(0),                                                         #But the address has deposited in that pool
                Txn.assets[0] == CID_L(Itob(i.load())),                                     #The user has a deposit active for that asa
            )
        ),

        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.asset_amount: UST(Itob(i.load())),
                TxnField.fee: Int(0),
                TxnField.xfer_asset: Txn.assets[0],
                TxnField.asset_receiver: Txn.sender()
            }
        ),
        InnerTxnBuilder.Submit(),

        App.localDel(Txn.sender(), Itob(i.load())),

        Approve()
    ])

    on_pool_delete = Seq([
        Assert(
            And(
                Txn.assets.length() == Int(1),
                Txn.accounts.length() == Int(0),
                Txn.sender() == MG,
                Global.group_size() == Int(1),
                Txn.type_enum() == TxnType.ApplicationCall,
                Txn.fee() == Int(2*TX_FEE),
                Txn.rekey_to() == Global.zero_address(),
                hasGlobalKey(Txn.application_args[1], Global.current_application_id()),                                                 #Check that the pool has been created
                Txn.assets[0] == CID_G(Txn.application_args[1]),
                Global.latest_timestamp() > ST(Txn.application_args[1]) + TD(Txn.application_args[1]),                                  #Check that the pool is ended
                Or(                                                                                                                     #Verify that:
                    UN(Txn.application_args[1]) == Int(0),                                                                              #Or there are no user that should claim
                    Global.latest_timestamp() > ST(Txn.application_args[1]) + TD(Txn.application_args[1]) + Int(MAX_SECONDS_TO_CLAIM)   #Or that the max time to claim is passed 
                )
            )
        ),

        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.fee: Int(0),
                TxnField.asset_receiver: Txn.sender(),
                TxnField.asset_amount: TBC(Txn.application_args[1]),
                TxnField.xfer_asset: Txn.assets[0],
            }
        ),
        InnerTxnBuilder.Submit(),

        App.globalDel(Txn.application_args[1]),

        App.globalPut(
            Bytes("INFO"),
            Concat(
                ExtractBytesFromGlobalKey(Bytes("INFO"), Int(0), Int(32)),
                Itob(POOL_NUM - Int(1))
            )

        ),

        Approve()
    ])

    program = Cond(
        [Txn.application_id() == Int(0), on_creation],
        [Txn.on_completion() == OnComplete.OptIn, handle_optin],
        [Txn.on_completion() == OnComplete.CloseOut, handle_closeout],
        [Txn.on_completion() == OnComplete.UpdateApplication, handle_updateapp],
        [Txn.on_completion() == OnComplete.DeleteApplication, handle_deleteapp],
        [And(
            Txn.on_completion() == OnComplete.NoOp,
            And(
                Txn.application_args.length() == Int(1),
                Txn.application_args[0] == Bytes("OI")
            )
        ), opt_in_asset],
        [And(
            Txn.on_completion() == OnComplete.NoOp,
            And(
                Txn.application_args.length() == Int(3),
                Txn.application_args[0] == Bytes("CP")
            )
        ), on_pool_create],
        [And(
            Txn.on_completion() == OnComplete.NoOp,
            And(
                Txn.application_args.length() == Int(2),
                Txn.application_args[0] == Bytes("DP"),
            )
        ), on_deposit],
        [And(
            Txn.on_completion() == OnComplete.NoOp,
            And(
                Txn.application_args.length() == Int(2),
                Txn.application_args[0] == Bytes("CL"),
            )
        ), on_claim],
        [And(
            Txn.on_completion() == OnComplete.NoOp,
            And(
                Txn.application_args.length() == Int(2),
                Txn.application_args[0] == Bytes("WD"),
            )
        ), on_withdrawal],
        [And(
            Txn.on_completion() == OnComplete.NoOp,
            And(
                Txn.application_args.length() == Int(2),
                Txn.application_args[0] == Bytes("DL"),
            )
        ), on_pool_delete],
    )
    return compileTeal(program, Mode.Application, version=5, assembleConstants=True)

def clear_state_program():
    program = Seq([
            i.store(Int(1)),

            While(i.load() < Int(MAX_LOCAL_BYTES + 1))
            .Do(
                Seq([
                    If(hasLocalKey(Txn.sender(), Itob(i.load())))
                    .Then(
                        Seq([
                            pool_id.store(ExtractBytesFromLocalKey(Txn.sender(), Itob(i.load()), Int(0), Int(8))),
                            If(hasGlobalKey(pool_id.load(), Global.current_application_id()))
                            .Then(
                                App.globalPut(
                                    pool_id.load(),
                                    Concat(
                                        ExtractBytesFromGlobalKey(pool_id.load(), Int(0), Int(8)),
                                        Itob(UN(pool_id.load()) - Int(1)),                          #Decrement the total users
                                        ExtractBytesFromGlobalKey(pool_id.load(), Int(16), Int(8)),
                                        Itob(TS(pool_id.load()) - UST(Itob(i.load()))),             #Decrement the Total staked
                                        Itob(TSC(pool_id.load()) - USC(Itob(i.load()))),            #Decrement the Total score
                                        ExtractBytesFromGlobalKey(pool_id.load(), Int(40), Int(24))
                                    )
                                )
                            )
                        ])
                    ),
                    i.store(i.load() + Int(1))
                ])
            ),
            
            Approve()
    ])
    return compileTeal(program, Mode.Application, version=5, assembleConstants=True)



def convert_to_teal():
    with open("approval_program.teal", "w") as f:
        approval_program_teal = approval_program()
        f.write(approval_program_teal)

    with open("clear_program.teal", "w") as f:
        clear_state_program_teal = clear_state_program()
        f.write(clear_state_program_teal)


if __name__ == "__main__":
    convert_to_teal()