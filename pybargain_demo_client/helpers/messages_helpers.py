#!/usr/bin/env python

import json
import urllib2
from pybargain_protocol.constants import MESSAGE_TYPES



'''
CONSTANTS
'''
# Defines some usefull constants
VALID_MEDIA_TYPES = ['application/bitcoin-' + mt for mt in MESSAGE_TYPES]

# seller_data keys
BDATA_NEGO_ID = 'nid'


'''
HTTP REQUEST
'''
def check_req_format(req):
    '''
    Checks if http request has a valid format (mime type and encoding)
    
    Parameters:
        req = http request
    '''
    ct_heads = req.headers.get('Content-Type','').split(';')
    valid_content_type =  any([(ct in VALID_MEDIA_TYPES) for ct in ct_heads])
    valid_encoding = req.headers.get('Content-Transfer-Encoding','') == 'binary'
    return valid_content_type and valid_encoding


def send_msg(msg, uri, next_msg_types):
    '''
    Sends a BargainingMessage to a given uri
    Returns the response
    
    Parameters:
        msg            = BargainingMessage to be sent
        uri            = remote bargaining uri 
        next_msg_types = list of expected message types for the next message
    '''
    if (msg is None) or (not msg.pbuff) or (not uri): return None
    
    req = urllib2.Request(uri.encode('utf-8'))
    req.add_header('User-agent', 'Mozilla/5.0')
    req.add_header('Content-Type', 'application/bitcoin-%s' % msg.msg_type)
    req.add_header('Content-Transfer-Encoding', 'binary')
    next_msg_types = ['application/bitcoin-%s' % nmt for nmt in next_msg_types]
    ser_acc_head = ','.join(next_msg_types)
    req.add_header('Accept', ser_acc_head)
    
    req.add_data(msg.pbuff)
    return urllib2.urlopen(req)
     
    

'''
SELLER DATA
'''
def get_buyer_data(msg):
    '''
    Extracts the buyer data from a BargainingMessage and returns a dictionary
    
    Parameters:
        msg = BargainingMessage
    '''
    if msg is None or msg.details is None: return {}
    sdata = msg.details.buyer_data
    if sdata: return json.loads(sdata)
    else: return {}


def build_buyer_data(nid = ''):
    '''
    Builds and serializes the buyer_data structure
    
    Parameter:
        nid = negotiation id
    '''
    sdata = dict()
    if nid: sdata[BDATA_NEGO_ID] = nid
    return json.dumps(sdata)



    