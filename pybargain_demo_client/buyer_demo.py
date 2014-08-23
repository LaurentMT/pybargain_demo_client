#!/usr/bin/env python

import json
import uuid
import calendar
from decimal import Decimal
from datetime import datetime
from functools import update_wrapper
from flask.app import Flask
from flask.globals import session, request
from flask.helpers import make_response
from flask.templating import render_template
from bitcoin.transaction import deserialize
from pybargain_protocol.constants import *
from pybargain_protocol.negotiation import Negotiation
from pybargain_protocol.bargaining_message import BargainingMessage
from pybargain_protocol.helpers.build_check_tx import SATOSHIS_TO_BITCOIN
from services.nego_db_service import NegoDbService
from helpers.wallet_helper import get_balance
from services.negotiator_service import NegotiatorService
from helpers.messages_helpers import check_req_format, send_msg



'''
CONSTANTS
'''
NETWORK = TESTNET

# The seller uri (received from a link, qrcode, ...)
SELLER_URI = 'http://127.0.0.1:8082/bargain'




'''
INITIALIZATION
'''
# Initializes the flask app
app = Flask(__name__)

# Initializes a secret key used to encrypt data in cookies
app.secret_key = '\xfd{H\xe5<\x95\xf9\xe3\x96.5\xd1\x01O<!\xd5\xa2\xa0\x9fR"\xa1\xa8'


# Initializes services to access databases or services
# For this toy project we use fake dbs storing data in memory
nego_db_service = NegoDbService()
negotiator = NegotiatorService(NETWORK)


'''
FLASK UTILITY METHODS
'''
# NoCache decorator 
# Required to fix a problem with IE which caches all XMLHttpRequest responses 
def nocache(f):
    def add_nocache(*args, **kwargs):
        resp = make_response(f(*args, **kwargs))
        resp.headers.add('Last-Modified', datetime.now())
        resp.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0')
        resp.headers.add('Pragma', 'no-cache')
        return resp
    return update_wrapper(add_nocache, f)

# Reverse filter for templates
@app.template_filter('reverse')
def reverse_filter(s):
    return s[::-1]

@app.context_processor
def utility_processor():
    def format_date(ts):
        return datetime.utcfromtimestamp(ts).strftime("%d %b %Y %H:%M:%S")
    
    def format_price(amount):
        return '%s BTC' % str(amount / 100000000.0)
    
    def format_memo(memo):
        return memo if memo else '<No message>'
    
    def format_txs(txs):
        if txs is None: return ''
        return str([json.dumps(deserialize(tx)) for tx in txs])
    
    def format_raw_txs(txs):
        if txs is None: return ''
        return str(txs)    
    
    def format_outputs(outs):
        if outs is None: return ''
        return str(outs)
    
    def format_msg_header(msg):
        date = format_date(msg.details.time)
        if msg.msg_type == TYPE_BARGAIN_REQUEST:
            return '%s - (YOU) - %s' % (date, 'Request sent for a new negotiation')
        elif msg.msg_type == TYPE_BARGAIN_REQUEST_ACK:
            amount = format_price(msg.details.amount)
            tmp = 'Negotiation accepted with an initial offer of %s' % amount
            return '%s - (SELLER) - %s' % (date, tmp)
        elif msg.msg_type == TYPE_BARGAIN_PROPOSAL:
            amount = format_price(msg.details.amount)
            if msg.details.is_redeemable:
                tmp = 'Payment sent to seller: %s' % amount
            else:
                tmp = 'New offer %s' % amount
            return '%s - (YOU) - %s' % (date, tmp)
        elif msg.msg_type == TYPE_BARGAIN_PROPOSAL_ACK:
            amount = format_price(msg.details.amount)
            tmp = 'New offer %s' % amount
            return '%s - (SELLER) - %s' % (date, tmp)
        elif msg.msg_type == TYPE_BARGAIN_COMPLETION:
            tmp = 'Negotiation completed'
            return '%s - (SELLER) - %s' % (date, tmp)
        elif msg.msg_type == TYPE_BARGAIN_CANCELLATION:
            tmp = 'Negotiation cancelled'
            return '%s - %s' % (date, tmp)
        else:
            return ''
    
    def format_status(msg):
        if msg.status == MSG_STATUS_OK:
            return 'Valid and consistent' 
        elif msg.status == MSG_STATUS_UND:
            return 'To be checked'
        else:
            return 'Invalid<br/>' + '<br/>'.join(msg.errors)
        
    return dict(format_date=format_date, 
                format_price=format_price,
                format_memo=format_memo,
                format_txs=format_txs,
                format_raw_txs=format_raw_txs,
                format_outputs=format_outputs,
                format_msg_header=format_msg_header,
                format_status=format_status)


'''
END POINTS
'''

@app.route('/', methods=['GET'])
@app.route('/home', methods=['GET'])
def home():
    # Everytime someone accesses the homepage
    # we check if there's some old negotiations to remove from memory
    for nego in nego_db_service.get_all_negos():
        if nego.get_expiry_for_role(ROLE_BUYER) > long(calendar.timegm(datetime.now().timetuple())) + 3600L:
            nego_db_service.delete_nego(nego.nid)
    # Displays the homepage 
    return render_template('index.html')


@app.route('/tellmemore', methods=['GET'])
def tellmemore():
    return render_template('tellmemore.html')


@app.route('/feedthewallet', methods=['GET'])
@nocache
def feedthewallet():
    # Resets the current negotiation
    if session.has_key('nid'): del session['nid']
    params_tpl = {}
    params_tpl['wallet_blc'] = get_balance([negotiator.addr1])
    return render_template('feedthewallet.html', params_tpl=params_tpl)


@app.route('/negotiation', methods=['GET', 'POST'])
@nocache
def negotiation():
    errors = []  
   
    if session.get('nid', None) is None:
        # Generates a new negotiation if needed
        is_new_nego = True
        session['nid'] = str(uuid.uuid4())
        nego = Negotiation(session['nid'], ROLE_BUYER, TESTNET)
        nego_db_service.create_nego(session['nid'], nego)
    else:
        # Gets the negotiation
        is_new_nego = False
        nego = nego_db_service.get_nego_by_id(session['nid'])
            
    '''
    Prepares the BargainingMessage to be sent (if there's one)
    '''
    if is_new_nego:
        # CASE 1: We start a new negotiation
        # Builds a REQUEST message
        new_msg, errors = negotiator.process(nego)
    elif request.method == 'POST':
        # Case 2: We continue an existing negotiation
        # Gets data sent by the user
        container = request.get_json(False, True, False) if request.mimetype == "application/json" else request.form 
        amount    = int(Decimal(container['amount']) * SATOSHIS_TO_BITCOIN)
        memo      = container['memo']
        # Builds a new message (PROPOSAL or CANCEL) 
        # For this demo, we never send fees (test network)
        new_msg, errors = negotiator.process(nego, memo, amount)
    else:
        new_msg = None
        errors.append('Invalid HTTP method')              
    
    '''
    Sends the BargainingMessage
    '''
    if len(errors) == 0:
        # Appends the new message to the chain
        nego.append(new_msg)
        nego_db_service.update_nego(session['nid'], nego)
        # Sends the message
        next_msg_types = nego.get_next_msg_types()
        uri = SELLER_URI if (new_msg.msg_type == TYPE_BARGAIN_REQUEST) else nego.get_bargain_uri_for_role(ROLE_BUYER)
        response = send_msg(new_msg, uri, next_msg_types)
                
        '''
        Processes the response
        '''
        try:
            if response.code == 200:
                if check_req_format(response): 
                    pbuff = response.read()
                    msg = BargainingMessage.deserialize(pbuff)
                    if not nego.already_received(msg):     
                        if msg.check_msg_fmt(NETWORK): 
                            nego.check_consistency(msg)    
                        nego.append(msg)
                        nego_db_service.update_nego(session['nid'], nego)
            else:
                errors.append('Remote node returned an error')
        except:
            errors.append('A problem occurred while processing the message sent by the remote node')
        
    '''
    Prepares rendering 
    '''
    params_tpl = {}
    params_tpl['errors']     = '' if len(errors) == 0 else '\n'.join(errors)
    params_tpl['wallet_blc'] = get_balance([negotiator.addr1])
    params_tpl['chain']      = nego._msgchain
    params_tpl['completed']  = True if nego.status in {NEGO_STATUS_CANCELLED, NEGO_STATUS_COMPLETED} else False
    return render_template('negotiation.html', params_tpl=params_tpl)


if __name__ == '__main__':
    # Comment/uncomment following lines to switch "production" / debug mode
    #app.run(host='0.0.0.0', port=8083)
    app.run(debug=True, port=8083)
