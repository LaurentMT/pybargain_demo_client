#!/usr/bin/env python
from bitcoin.transaction import select
from pybargain_protocol.constants import TESTNET
from pybargain_protocol.helpers.bc_api import blockr_unspent
from pybargain_protocol.helpers.build_check_tx import build_tx_with_change


'''
UTILITY METHODS
'''
def get_balance(addr):
    '''
    Gets balance (in satoshis) associated to a list of addresses
    
    Parameters:
        addr = a list of testnet addresses
    '''
    if (addr is None) or (len(addr) == 0): return 0
    utxos = blockr_unspent(TESTNET, addr)
    return sum([utxo['value'] for utxo in utxos]) / 100000000.0


def build_single_tx(amount, fees, outputs, addr, privkey, network):
    '''
    Builds a tx for which:
        * sum(Tx_ins) = amount + fees
        * Tx_outs = outputs   
        * Tx_ins are owned by addr/privkey
        
    Parameters:
        amount  = amount proposed by the buyer
        fees    = fees proposed by the buyer
        outputs = outputs proposed by the seller
        addr    = address owning the utxos to be redeemed by the tx
        privkey = privkey associated to addr
        network = network used for the negotiation
    '''
    # TODO : Manage several addresses as sources of utxos
    
    # Gets utxos for self.addr1
    utxos = blockr_unspent(network, addr)
    try:
        # Selects utxos covering amount + fees
        inputs = select(utxos, amount + fees)
        for i in inputs: i['privkey'] = privkey
        # Builds and returns the tx 
        # For this demo, we send change to the sender address (but address reuse is bad)
        return build_tx_with_change(inputs, outputs, amount, fees, addr)
    except:
        return None
    