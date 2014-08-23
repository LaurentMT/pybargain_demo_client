#!/usr/bin/env python
'''
A class negotiating to sell a product/service
Implements a very basic strategy
'''
import calendar
from datetime import datetime
from bitcoin.main import sha256, privtopub, pubtoaddr
from bitcoin.transaction import address_to_script
from pybargain_protocol.constants import *
from pybargain_protocol.bargaining_cancellation import BargainingCancellationDetails
from pybargain_protocol.bargaining_message import BargainingMessage
from pybargain_protocol.bargaining_request import BargainingRequestDetails
from pybargain_protocol.bargaining_proposal import BargainingProposalDetails
from helpers.messages_helpers import build_buyer_data
from helpers.wallet_helper import build_single_tx



class NegotiatorService(object):
        
    '''
    ATTRIBUTES
    
    bargain_uri   = bargain uri used by the seller
    
    _privkey1     = first private key
    _pubkey1      = first public key
    addr1         = first address
    _script1      = first output script
    
    _privkeysign  = private key used to sign messages
    _pubkeysign   = public key used to sign messages
    '''
    
    
    def __init__(self, network, bargain_uri = ''):
        '''
        Constructor
        '''
        self.bargain_uri    = bargain_uri
        magicbytes          = MAGIC_BYTES_TESTNET if network == TESTNET else MAGIC_BYTES_MAINNET
        
        self._privkey1    = sha256('This is a private key')
        self._pubkey1     = privtopub(self._privkey1)  
        self.addr1        = pubtoaddr(self._pubkey1, magicbytes)  # mryyjA6YpPCJ24MsSN7YnCK6M3NZoUAwxb
        self._script1     = address_to_script(self.addr1) 
        
        self._privkeysign = sha256('This is a private key used to sign messages sent by the buyer')
        self._pubkeysign  = privtopub(self._privkeysign)  
        
    
    def process(self, nego = None, memo = '', amount = 0, fees = 0):
        '''
        Builds the next message for a given negotiation
        During negotiation phase, if amount equals 0, we consider that the user wants to send a CANCELLATION message
        Returns a tuple (next_msg, errors)
        
        Parameters:
            nego   = negotiation
            memo   = memo to be sent with the message
            amount = proposed amount
            fees   = proposed fees
        '''
        # Checks nego and expected next active role
        if nego is None: 
            return (None, ['Unable to find the negotiation'])
        if not (nego.get_next_active_role() == ROLE_BUYER): 
            return (None, ['Unable to send a new message. Still waiting for an answer from the seller'])
        
        msg      = None
        last_msg = nego.get_last_msg()
        
        # Tries to build the next message
        if (last_msg is None) and (nego.status == NEGO_STATUS_INITIALIZATION):
            msg = self._build_request_msg(last_msg, nego)
        elif last_msg.status == MSG_STATUS_KO:
            msg = self._build_cancel_msg(memo, last_msg, nego)
        elif last_msg.status == MSG_STATUS_OK:
            if nego.status == NEGO_STATUS_NEGOTIATION:
                if amount == 0:
                    msg = self._build_cancel_msg(memo, last_msg, nego)
                else:
                    msg = self._build_proposal_msg(memo, amount, fees, last_msg, nego)
        
        # Checks if a message has been built              
        if msg is None: return (None, ['Unable to send a new message in the current state of the negotiation'])
        
        # Checks message format and consistency
        if msg.check_msg_fmt(nego.network):
            # Signs the message
            msg.sign(last_msg, SIGN_ECDSA_SHA256, self._pubkeysign, self._privkeysign)
            if nego.check_consistency(msg):
                # Serializes the message 
                msg.pbuff = msg.serialize()
        
        return (msg, msg.errors)
                
    
    def _build_cancel_msg(self, memo, last_msg, nego):
        '''
        Builds a Cancellation message
        
        Parameters:
            memo     = memo to be sent with the message
            last_msg = last message received from seller            
            nego     = current negotiation
        '''
        time    = long(calendar.timegm(datetime.now().timetuple()))
        bdata   = build_buyer_data(nego.nid)
        sdata   = last_msg.details.seller_data
        dtls = BargainingCancellationDetails(time, bdata, sdata, memo)
        return BargainingMessage(TYPE_BARGAIN_CANCELLATION, dtls)
    
    
    def _build_request_msg(self, last_msg, nego):
        '''
        Builds a RequestACK message
        
        Parameters:
            last_msg = last message received from buyer            
            nego     = current negotiation
        '''
        time    = long(calendar.timegm(datetime.now().timetuple()))
        bdata   = build_buyer_data(nego.nid)
        network = nego.network
        expires = time + 1800L # 30 minutes
        uri     = self.bargain_uri
        dtls = BargainingRequestDetails(time, bdata, '', network, expires, uri) 
        return BargainingMessage(TYPE_BARGAIN_REQUEST, dtls)
    
    
    def _build_proposal_msg(self, memo, amount, fees, last_msg, nego):
        '''
        Builds a Proposal message
        
        Parameters:
            memo     = memo to be sent with the message
            amount   = proposed amount
            fees     = proposed fees
            last_msg = last message received from buyer
            nego     = current negotiation
        '''
        time        = long(calendar.timegm(datetime.now().timetuple()))
        bdata       = build_buyer_data(nego.nid)
        sdata       = last_msg.details.seller_data
        tx          = build_single_tx(amount, fees, last_msg.details.outputs, self.addr1, self._privkey1, nego.network)
        # For this demo, we refund to the sender address (but address reuse is bad)
        refund      = [{'script': self._script1}]
        redeemable  = True if amount >= last_msg.details.amount else False
        dtls = BargainingProposalDetails(time, bdata, sdata, [tx], memo, refund, amount, fees, redeemable)
        return BargainingMessage(TYPE_BARGAIN_PROPOSAL, dtls)
        
    
        
    