#!/usr/bin/env python
'''
A class simulating a wrapper to access a database storing Negotiations.
For this toy project, we store Negotiations in memory.
'''

class NegoDbService(object):
    
    def __init__(self):
        # Initializes some dictionaries to store negotiations
        self._negos_by_id = dict()
                
    def create_nego(self, nid, nego):
        '''
        Create a nego entry in db
        Parameters:
            nid  = id of the negotiation
            nego = nego object to store in db
        '''
        # Checks parameter
        if not self._check_nego(nego):
            return False
        # Checks that a nego with same id has not already been stored in db
        if self.get_nego_by_id(nid) is None:
            # Creates the user in db
            self._negos_by_id[nid] = nego
            return True
        else:
            return False  
            
    def update_nego(self, nid, nego):
        '''
        Update a nego entry in db
        Parameters:
            nid  = id of the negotiation
            nego = nego object to update in db
        '''
        # Checks parameter
        if not self._check_nego(nego):
            return False
        # Checks that a nego with same id exists in db
        if not (self.get_nego_by_id(nid) is None):
            # Updates the nego in db
            self._negos_by_id[nid] = nego
            return True
        else:
            return False  
        
    def delete_nego(self, nid):
        '''
        Delete a nego entry from db
        Parameters:
            nid = id of the negotiation
        '''
        # Checks parameter
        if not nid: return False
        # Checks that a nego with same id exists in db
        if not (self.get_nego_by_id(nid) is None):
            del self._negos_by_id[nid]
            return True
        else:
            return False
        
    def get_nego_by_id(self, nid):
        '''
        Gets a nego associated to a given id
        Parameters:
            nid = id of the negotiation
        '''
        return self._negos_by_id.get(nid, None) if nid else None   
    
    def get_all_negos(self):
        '''
        Gets a list of all negotiations
        '''
        return self._negos_by_id.values()
    
    def _check_nego(self, nego):
        if nego is None: return False
        else: return True     
        
    
    
