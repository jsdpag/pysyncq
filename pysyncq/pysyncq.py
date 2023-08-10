
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
        
        # Sender string and is uninitialised. But instance queue position isn't.
        self.sender = None
        self.i      = 0
        
        # Prepare screening sets for message sender and message type
        self.scrnsend = set( )
        self.scrntype = set( )
        
        # Create a new condition variable that will govern all access to the
        # shared memory.
        self.cond = mp.Condition( )
        
        # Create the shared memory
        self.shm = sm.SharedMemory( name , create , size )
        
        # Guarantee that it is initialised to zeros. Has effect of setting queue
        # header process count and head and tail positions to zero, as well.
        self.shm.buf[:] = bytes( size )
        
        # Make a memoryview that sees only the queue header. Each indexed unit
        # is of the queue's counter type e.g. unsigned long long integer.
        self.h = self.shm.buf[ : hdr.sizequeuehead ].cast( hdr.fmtqueuehead )
        
        # Another memoryview sees only the queue body, where the messages go.
        # Since we will have no idea how long each message will be, we need the
        # index granularity to be at the level of each byte.
        self.b = self.shm.buf[ hdr.sizequeuehead : ]
        
        # Set number of free bytes in the queue main body.
        self.h[ hdr.ifree ] = len( self.b )
        

    def  __str__ ( self ) :
        
        return f'PySyncQ(name={self.name},size={self.size})'
    
    
    #-- Single underscore methods for internal class use --#
    
    def  _next ( self ) :
    
        '''
        _next looks for the next message in the queue relative to current read
        position of this instance in attribute .i. If there is a message to read
        then a memoryview of the message counters is returned, along with the
        location of the first byte past the counters in a tuple with the format
        ( memoryview , byte-location ); the instance read position is put to the
        first byte past the end of the message body. However, if there is no
        message to read then False is returned. 
        '''
        
        # Flag lowered if a message is available
        msgflg = True
        
        # Get the queue's lock
        with  self.cond :
        
            # The queue is empty, there is no message
            if  self.h[ hdr.ifree ] == len( self.b ) : return False
            
            # Keep looking so long as the read position hasn't reached the tail
            while  self.i != self.h[ hdr.itail ] :
            
                # Read position is too close to the end of the queue body for
                # a full set of message counters.
                if  len( self.b ) - self.i < hdr.nbytemsghead :

                    # The next message will be at the start of the queue body.
                    self.i = 0
                
                # We have a contiguous set of message counters. Raise flag and
                # break the infinite loop.
                else :
                
                    msgflg = False
                    break
                    
        # There is no message available
        if  msgflg : return False
        
        # Cast memoryview of message's counters
        hmsg = \
            self.b[ self.i : self.i + hdr.nbytemsghead ].cast( hdr.fmtmsghead )
        
        # Locate the first byte past the message counters
        b = ( self.i + hdr.nbytemsghead  )  %  len( self.b )
        
        # Set read position to first byte past the end of message body
        self.i = ( b + hmsg[ hdr.isend ] + hmsg[ hdr.itype ] + 
                       hmsg[ hdr.ibody ] )  %  len( self.b )
        
        # Return message details
        return  ( hmsg , b )
    

    #-- Principal API methods --#
    
    # Creation / Deletion #
    
    def  open ( self , sender = str( mp.current_process( ).pid ) ,
                       filtself = True ) :
    
        '''
        open( sender = pid , filtself = True ) registers the current process
        with the queue. sender is a string naming the process in each message
        that it sends. By default, this is the current process ID i.e. pid.
        Messages filtself 
        '''
        
        # Store sender string as bytes that can go directly into shared memory
        self.sender = sender.encode( )
        
        # If true then add local sender name to message filter list
        if  filtself : self.scrnsend.add( sender )
        
        # Get queue lock. Increment the process counter in the queue header. And
        # set this instance's read or queue position to the tail; read only the
        # messages that come after this instance/process has registered.
        with  self.cond :
            self.h[ hdr.iproc ] += 1
            self.i = self.h[ hdr.itail ]
        
    
    def  close ( self ) :
        
        '''
        Closes and unlinks the shared memory.
        '''
        
        # Get queue lock and decrement the process counter in the queue header.
        # But remember the counter value for after the shared memory is closed. 
        with  self.cond :
            if self.h[ hdr.iproc ] : self.h[ hdr.iproc ] -= 1
            noproc = self.h[ hdr.iproc ] == 0
            # Decrement read counter on any unread messages
        
        # Take care to release memoryviews, or else .close raises an exception.
        self.h.release( )
        self.b.release( )
        
        # Close local copy of shared memory
        self.shm.close ( )
        
        # Unlink if this is the last close
        if  noproc : self.shm.unlink( )


    # Message handling #
    
    def  append ( self , msgtype = '' , msg = '' , block = False ,
                         timer = 0.5 ) :
    
        '''
        append ( self , msgtype = '' , msg = '' , block = False , timer = 0.5 )
        
        Adds a new message to the tail of the queue. The message header stores
        the sender name and message type string.The msg forms the main body of
        the message.
        
        If the queue lacks sufficient free space in which to write the message
        header and body then a MemoryError exception is raised, unless block is
        True. Then append will wait until there is enough room in the queue.
        
        append will wait indefinitely for free space if timer is None. But timer
        can be a float that specifies the number of seconds to wait for. If the
        timer expires before the message is appended to the queue then the
        MemoryError exception is raise.
        '''
        
        # Internally, messages have the format
        # [ message counters , message sender , message type , message body ]
        
        # Cast type and message strings to bytes
        btype = msgtype.encode( )
        bmsg  =     msg.encode( )
        
        # Total number of bytes required by the message, including counters
        n = hdr.sizemsghead + len( self.sender ) + len( btype ) + len( bmsg )
        
        # Build a predicate function that returns True when there is enough
        # space in the queue for the message.
        free = lambda : self.h[ hdr.ifree ] >= n
        
        # Get queue lock, the remainder of append runs with possession of lock
        with  self.cond :
        
            # The queue is too full
            if  not ( free( )  or  block  and  
                                   self.cond.wait_for( free , timer ) ) :
            
                raise  MemoryError( f'{ n } byte message > '
                                    f'{ self.h[ hdr.ifree ] } free bytes.' )
                
            # If we got here then there is enough free space in the queue. Get
            # position of queue's tail, which is where the message write starts.
            i = self.h[ hdr.itail ]
            
            # Create a memoryview for the message header counters
            hmsg = self.b[ i : i + hdr.sizemsghead ].cast( hdr.fmtmsghead )
            
            # Load message counters. Number of reads from message must equal the
            # number of registered processes, one read per process.
            hmsg[ hdr.iread ] = self.h[ hdr.iproc ]
            hmsg[ hdr.isend ] = len( self.sender )
            hmsg[ hdr.itype ] = len( btype )
            hmsg[ hdr.ibody ] = len( bmsg )
            
            # Advance the byte index past the message counters
            i += hdr.sizemsghead
            
            # Byte strings
            for  b  in  ( self.sender , btype , bmsg ) :
                
                # Bytes remaining prior to the end of the queue body
                r = len( self.b ) - i
                
                # The string will fit in a contiguous block
                if  r >= len( b ) :
                
                    # Slice assign the entire byte string
                    self.b[ i : i + len( b ) ] = b
                    
                    # Advance write position to next free byte
                    i += len( b )
                    
                # The queue is a circular buffer. Bisect the string between the
                # end of the queue body and the start.
                else :
                    
                    # Slice assign what we can to the end of the queue body
                    self.b[ i : ] = b[ : r ]
                    
                    # Number of bytes from string that are still unwritten
                    r = len( b ) - r
                    
                    # Cycle to the start of the queue body and write remainder
                    self.b[ : r ] = b[ -r : ]
                    
                    # Write position at next free byte
                    i = r
            
            # Decrement length of message from queue's free space counter
            self.h[ hdr.ifree ] -= n
            
            # Find next byte past new message, the new tail position.
            self.h[ hdr.itail ] = i
            
            # Message counters require contiguous bytes. But the new tail
            # position is too close to the end of the queue body for that. We
            # must position the tail at the start of the queue body and discard
            # the bytes at the end.
            if  ( r := len( self.b ) - self.h[ hdr.itail ] ) < hdr.sizemsghead :
                self.h[ hdr.itail ]  = 0
                self.h[ hdr.ifree ] -= r
            
            # Wake up any process that is waiting on the state of the queue
            self.cond.notify_all( )
        
        # Dropped out of with statement - queue lock has been released. But the
        # message counter memoryview remains. It refers to the shared memory,
        # which cannot close properly until this memoryview has been released.
        # We do it explicitly, in case the object is not destroyed through
        # garbage collection before the .close method is invoked.
        hmsg.release( )
         
        
    def  pop ( self , block = False ) :
    
        '''
        Reads the next next unread message from the queue and returns the tuple
        ( sender , type , msg ) ... see append. If the sender or type string is
        found in the scrnsend or scrntype sets, respectively, then the message
        is skipped, and pop looks for the next unread message in the queue. If
        there are no unread messages then None is returned, unless block is
        True. Then pop will wait until there is a new message to read.
        '''
        
        # Locate next message - with lock
        # Copy message sender, type, and body if not filtered
        # Decrement read counter - with lock
        # Loop back if filtered else return read
        pass


