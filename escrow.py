from pyteal import *


def escrow(seed_addr: str):
    seeder = Addr(seed_addr)

    is_valid_seed = And(
        Global.group_size() == Int(3),
        # Seed with funds
        Gtxn[0].type_enum() == TxnType.Payment,
        Gtxn[0].sender() == seeder,
        Gtxn[0].amount() == Int(int(0.3 * 1e6)),  # 0.3 algos
        Gtxn[0].close_remainder_to() == Global.zero_address(),
        # Opt escrow into asset
        Gtxn[1].type_enum() == TxnType.AssetTransfer,
        Gtxn[1].asset_amount() == Int(0),
        Gtxn[1].asset_receiver() == Gtxn[1].sender(),
        Gtxn[1].asset_receiver() == Gtxn[0].receiver(),
        # Xfer asset from creator to escrow
        Gtxn[2].type_enum() == TxnType.AssetTransfer,
        Gtxn[2].asset_amount() == Int(1),
        Gtxn[2].asset_receiver() == Gtxn[0].receiver(),
        Gtxn[2].sender() == Gtxn[0].sender(),
        Gtxn[2].asset_close_to() == Global.zero_address(),
        Gtxn[2].xfer_asset() == Gtxn[1].xfer_asset(),
    )

    is_valid_claim = And(
        Global.group_size() == Int(3),
        If(Txn.group_index() == Int(1))
        .Then(Ed25519Verify(Txn.tx_id(), Arg(0), Tmpl.Bytes("TMPL_GEN_ADDR")))
        .Else(Int(1)),
        # Account Opt in
        Gtxn[0].type_enum() == TxnType.AssetTransfer,
        Gtxn[0].sender() == Gtxn[0].asset_receiver(),
        Gtxn[0].asset_amount() == Int(0),
        Gtxn[0].asset_close_to() == Global.zero_address(),
        # Close Asset to Account
        Gtxn[1].type_enum() == TxnType.AssetTransfer,
        Gtxn[1].asset_amount() == Int(0),
        Gtxn[1].xfer_asset() == Gtxn[0].xfer_asset(),
        Gtxn[1].asset_close_to() == Gtxn[0].sender(),
        # Close algos back to seeder
        Gtxn[2].type_enum() == TxnType.Payment,
        Gtxn[2].amount() == Int(0),
        Gtxn[2].close_remainder_to() == seeder,
    )

    is_valid_recover = And(
        Global.group_size() == Int(3),
        # Make sure seeder cosigned
        Gtxn[0].type_enum() == TxnType.Payment,
        Gtxn[0].sender() == seeder,
        Gtxn[0].receiver() == seeder,
        Gtxn[0].amount() == Int(0),
        Gtxn[0].close_remainder_to() == Global.zero_address(),
        Gtxn[0].rekey_to() == Global.zero_address(),
        # Close out asset
        Gtxn[1].type_enum() == TxnType.AssetTransfer,
        Gtxn[1].asset_amount() == Int(0),
        Gtxn[1].asset_close_to() == seeder,
        # Close out algos
        Gtxn[2].type_enum() == TxnType.Payment,
        Gtxn[2].amount() == Int(0),
        Gtxn[2].close_remainder_to() == seeder,
    )

    return Cond(
        [Gtxn[0].sender() == seeder, Return(Or(is_valid_seed, is_valid_recover))],
        [Gtxn[0].sender() != seeder, Return(is_valid_claim)],
    )


def get_contract(seeder: str) -> str:
    return compileTeal(
        escrow(seeder), mode=Mode.Signature, version=5, assembleConstants=True
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--funder", help="Address used to fund escrow accounts", required=True
    )
    args = parser.parse_args()

    with open("escrow.tmpl.teal", "w") as f:
        f.write(get_contract(args.funder))
