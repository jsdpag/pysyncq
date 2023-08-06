
'''
Python Synchronisation Queue
'''

#--- IMPORT BLOCK ---#

# Standard library
import multiprocessing               as mp
import multiprocessing.shared_memory as sm

# From pysyncq ... improve this by referencing the parent package
import header as hdr


#--- PRINCIPAL API ---#

class  PySyncQ :

    '''
    class pysyncq.PySyncQ( name = None , create = False , size = <Page Size> )

    Creates a synchronisation queue. name is a str that names the shared memory
    that is the backbone of the queue, and to which all processes will connect.
    create is a bool that signals whether to create new shared memory (True) or
    to use existing shared memory (False). size is an int of 0 or greater giving
    the number of bytes to request for the shared memory.  
    '''

    #-- Double underscore methods --#

    def  __init__ ( self , name = None , create = False , size = hdr.defsize ) :
    
        # Remember initialisation parameters, size is especially important
        self.name = name
        self.create = create
        self.size = size
        
        # Prepare screening sets for message sender and message type
        self.scrnsend = set( )
        self.scrntype = set( )
        
        # Create a new condition variable that will govern all access to the
        # shared memory.
        self.cond = mp.Condition( )
        
        # Create the shared memory
        
        


    def  __str__ ( self ) :
        
        return f'PySyncQ(name={self.name},size={self.size})'
    
    
    #-- Single underscore methods for internal class use --#
        

    #-- Principal API methods --#
    
    def  close ( self ) :
        
        print( 'Close and unlink shared memory.' )
        
