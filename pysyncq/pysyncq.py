
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
        
        # Sender string and self-filtering bool are uninitialised
        self.sender   = None
        self.filtself = None
        
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
        self.h = self.shm.buf[ : hdr.sizequeuehead ].cast( hdr.fmtqueuehead )
        
        # Another memoryview sees only the queue body, where the messages go.
        # Since we will have no idea how long each message will be, we need the
        # index granularity to be at the level of each byte.
        self.b = self.shm.buf[ hdr.sizequeuehead : ]


    def  __str__ ( self ) :
        
        return f'PySyncQ(name={self.name},size={self.size})'
    
    
    #-- Single underscore methods for internal class use --#
        

    #-- Principal API methods --#
    
    # Creation / Deletion #
    
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
        
        # Take care to release memoryviews, or else .close raises an exception.
        self.h.release( )
        self.b.release( )
        
        # Close local copy of shared memory
        self.shm.close ( )
        
        # Unlink if this is the last close
        if  noproc : self.shm.unlink( )


    # Message handling #
    
    def  append ( self , type = None , msg = '' , block = False ) :
    
        '''
        append ( self , type = None , msg = '' , block = False ) adds a new
        message to the head of the queue. The message header stores the sender
        name and type string.The msg forms the main body of the message. A
        successful write to the queue returns False. But if there is no room in
        the queue for the message then True is returned, unless block is True.
        Then append will wait until there is enough room for the message, and
        False is returned.
        '''
        
        pass
        
        
    def  pop ( self , block = False ) :
    
        '''
        Reads the next next unread message from the queue and returns the tuple
        ( sender , type , msg ) ... see append. If the sender or type string is
        found in the scrnsend or scrntype sets, respectively, then the message
        is skipped, and pop looks for the next unread message in the queue. If
        there are no unread messages then None is returned, unless block is
        True. Then pop will wait until there is a new message to read.
        '''
        
        pass


