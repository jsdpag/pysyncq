
'''
Python Synchronisation Queue
'''

#--- IMPORT BLOCK ---#

# Standard library
import multiprocessing               as mp
import multiprocessing.shared_memory as sm

# From pysyncq package
from pysyncq import header as hdr


#--- PRINCIPAL API ---#

class  PySyncQ :

    '''
    class pysyncq.PySyncQ( name = None , create = True , size = <Page Size> )

    Creates a synchronisation queue. name is a str that names the shared memory
    that is the backbone of the queue, and to which all processes will connect.
    create is a bool that signals whether to create new shared memory (True) or
    to use existing shared memory (False). size is an int of 0 or greater giving
    the number of bytes to request for the shared memory.
    
    Each process that wishes to read/write on the queue must make a separate
    call to the .open( ) method, in order to register itself with the queue as
    a unique reader/writer.
    '''

    #-- Double underscore methods --#

    def  __init__ ( self , name = None , create = True , size = hdr.defsize ) :
    
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
        self.shm = sm.SharedMemory( name , create , size )
        
        # Guarantee that it is initialised to zeros
        self.shm.buf[:] = bytes( size )
        
        # Make a memoryview that sees only the queue header. Each indexed unit
        # is of the queue's counter type e.g. unsigned long long integer.
        self.h = self.shm.buf[ : hdr.sizeqh ].cast( hdr.fmtcnt )
        
        # Another memoryview sees only the queue body, where the messages go.
        self.b = self.shm.buf[ hdr.sizeqh : ]


    def  __str__ ( self ) :
        
        return f'PySyncQ(name={self.name},size={self.size})'
    
    
    #-- Single underscore methods for internal class use --#
        

    #-- Principal API methods --#
    
    def  open ( self , sender = str( mp.current_process( ).pid ) ,
                       filtself = True ) :
    
        '''
        .open( sender = pid , filtself = True ) registers the current process
        with the queue. sender is a string naming the process in each message
        that it sends. By default, this is the current process ID i.e. pid.
        Messages filtself 
        '''
        
        # Store sender string as bytes that can go directly into shared memory
        self.sender = sender.encode( )
        
        # And remember if messages from the current process should be filtered
        self.filtself = filtself
        
        # If true then add local sender name to message filter list
        if  filtself : self.scrnsend.add( sender )
        
        # Get queue lock and increment the process counter in the queue header
        with  self.cond : self.h[ hdr.iproc ] += 1
        
    
    def  close ( self ) :
        
        '''
        Closes and unlinks the shared memory.
        '''
        
        # Get queue lock and decrement the process counter in the queue header.
        # But remember the counter value for after the shared memory is closed. 
        with  self.cond :
            self.h[ hdr.iproc ] -= 1
            noproc = self.h[ hdr.iproc ] == 0
        
        # Take care to release memoryviews
        self.h.release( )
        self.b.release( )
        
        # Close local copy of shared memory
        self.shm.close ( )
        
        # Unlink if this is the last close
        if  noproc : self.shm.unlink( )


