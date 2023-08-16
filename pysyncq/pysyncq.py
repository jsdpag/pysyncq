
'''
Python Synchronisation Queue
'''

#--- IMPORT BLOCK ---#

# Standard library
from time import time
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
    
        # Size must not allow more messages than a queue header counter max val.
        if  size > hdr.maxshmemory :
            raise  MemoryError( f'Queue size can\'t exceed { hdr.maxshmemory }')
        
        # Remember initialisation parameters, size is especially important
        self.name = name
        self.create = create
        self.size = size
        
        # Sender string and is uninitialised. Instance read position is
        # initialised to first byte of queue body. The serial number of the
        # latest read done by this instance is initialised to zero.
        self.sender = None
        self.i      = 0
        self.slno   = 0
        
        # Prepare screening sets for message sender and message type. Pack them
        # together in a tuple for easy zipping.
        self.scrnsend = set( )
        self.scrntype = set( )
        self.scrns = ( self.scrnsend , self.scrntype )
        
        # Create a new condition variable that will govern all access to the
        # shared memory.
        self.cond = mp.Condition( )
        
        # Create the shared memory
        self.shm = sm.SharedMemory( name , create , size )
        
        # Guarantee that it is initialised to zeros. Has effect of setting queue
        # header process count and head and tail positions to zero, as well as
        # the message or write serial number.
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
    
    def  _popred ( self ) :
        
        '''
        _popred is a predicate function that returns True when the instance
        read position does not equal the queue tail position. Or when the read
        serial number does not equal the write serial number. Either condition
        signals a message that this instance hasn't read yet.
        
        DO NOT USE THIS unless the lock has been acquired, first.
        '''
        
        # Note, the logical or operator short-circuits. The serial
        # numbers are only checked if the instance read position sits at
        # the tail.
        return  ( self.i    != self.h[ hdr.itail ]  or
                  self.slno != self.h[ hdr.islno ] )
        
    
    def  _next ( self ) :
    
        '''
        _next looks for the next message in the queue relative to current read
        position of this instance in attribute .i. If there is a message to read
        then the function will yield a tuple containing a memoryview of the
        message counters and the location of the first byte that is past them,
        with the format ( memoryview , byte-location ). The instance read
        position is placed to the first byte past the end of the message body.
        
        Therefore, the function returns a generator that can be run in a loop.
        Once there is no longer any message to read then the function terminates
        and implicitly triggers a StopIteration exception. 
        '''
        
        # Generator loop
        while  True :
            
            # Get the queue's lock
            with  self.cond :
                
                # Queue is empty or pop predicate fails. There is no message.
                if self.h[ hdr.ifree ] == len( self.b ) or not self._popred( ) :
                    return
            
            # Increment instance read serial number, modulo max queue count val.
            if  self.slno == hdr.maxqueuehead :
                self.slno  = 0
            else :
                self.slno += 1
            
            # Cast memoryview of message's counters
            hmsg = \
             self.b[ self.i : self.i + hdr.sizemsghead ].cast( hdr.fmtmsghead )
            
            # Locate the first byte past the message counters
            b = ( self.i + hdr.sizemsghead  )  %  len( self.b )
            
            # Set read position to first byte past the end of message body
            self.i = ( b + sum( hmsg[hdr.mbcnt] ) )  %  len( self.b )

            # If the read position is too close to the end of the queue body for
            # a complete set of message counters to fit then it must skip those
            # final bytes and go back to the start of the queue body.
            if  len( self.b ) - self.i  <  hdr.sizemsghead :

                self.i = 0
            
            # Generate message details
            yield  ( hmsg , b )
            

    def  _read ( self , b , db ) :
        
        '''
        Read db bytes from queue body, starting at byte b. If b is less than db
        bytes from the end of the queue then the read wraps around to the start
        of the queue body and returns a concatenated result.
        
        Returns tuple ( bstr , b ). bstr is the byte string that is read from
        the queue body. b is the first byte past the end of the read, modulo
        queue body size.
        '''
        
        # Number of bytes readable before the end of the queue body
        n = min( db , len( self.b ) - b )
        
        # Read out bytes
        bstr = self.b[ b : b + n ].tobytes( )
        
        # Read must wrap around to start of queue body
        if  n < db : bstr += self.b[ : db - n ].tobytes( )
        
        # Advance b past the read
        b = ( b + db )  %  len( self.b )
        
        # Return the byte string
        return  bstr , b


    def  _free ( self , h ) :
        
        '''
        Free queue memory that stores message with header counter memoryview h.
        It is assumed that this message is at the queue head and that its read
        count is depleted.
        
        DO NOT USE THIS unless the lock has been acquired, first.
        '''
        
        # Bytes in message, including counters and all byte strings
        n = hdr.sizemsghead  +  sum( h[ hdr.mbcnt ] )
        
        # Advance head of queue, modulo size of queue body
        self.h[ hdr.ihead ] = ( self.h[ hdr.ihead ] + n )  %  len( self.b )
        
        # Free up those bytes
        self.h[ hdr.ifree ] += n
        
        # Head is now too close to end of queue body for a full set of message
        # counters. Wrap around back to the start of queue body and free the
        # skipped bytes.
        if  ( n := len( self.b ) - self.h[ hdr.ihead ] )  <  hdr.sizemsghead :
            
            self.h[ hdr.ihead ]  = 0
            self.h[ hdr.ifree ] += n


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
        if  filtself : self.scrnsend.add( self.sender )
        
        # Get queue lock. Increment the process counter in the queue header. And
        # set this instance's read or queue position to the tail; read only the
        # messages that come after this instance/process has registered. The
        # assignment to attribute i should provoke any necessary copy-on-write.
        with  self.cond :
            self.h[ hdr.iproc ] += 1
            self.i = self.h[ hdr.itail ]
        
    
    def  close ( self ) :
        
        '''
        Closes and unlinks the shared memory.
        '''
        
        # Return immediately if shared memory was already closed
        if  not self.shm : return
        
        # Get queue lock.
        with  self.cond :
        
            # Scan through any unread messages and decrement the read counter.
            # Be careful to release memoryviews.
            for m in self._next( ) :
                
                m[ 0 ][ hdr.iread ] -= 1
                m[ 0 ].release( )
            
            # Decrement the process counter
            if self.h[ hdr.iproc ] : self.h[ hdr.iproc ] -= 1
            
            # But remember the counter value, we unlink if all instances closed.
            noproc = self.h[ hdr.iproc ] == 0
        
        # Take care to release memoryviews, or else .close raises an exception.
        self.h.release( )
        self.b.release( )
        
        # Close local copy of shared memory
        self.shm.close ( )
        
        # Unlink if this is the last close
        if  noproc : self.shm.unlink( )
        
        # Signal that shared memory has been closed by this instance
        self.shm = None


    # Message handling #
    
    def  append ( self , msgtype = '' , msg = '' , block = False ,
                         timer = 0.5 ) :
    
        '''
        append ( self , msgtype = '' , msg = '' , block = False , timer = 0.5 )
        
        Adds a new message to the tail of the queue. The message header stores
        the sender name and msgtype as message type. msg forms the main body of
        the message. If msgtype or msg are not already str or bytes then they
        are first cast to str before casting to bytes with the default encoding.
        
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
        
        def  argbytes ( arg ) :
            '''
            Guarantee that input args are converted to byte strings from the arg
            cast to str.
            '''
            return  arg  if  type( arg ) is bytes  else  str( arg ).encode( )
        
        # Cast message type and body to bytes
        btype = argbytes( msgtype )
        bmsg  = argbytes(     msg )
        
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
            
            # Increment the message serial number, modulo max value of counter
            if  self.h[ hdr.islno ] == hdr.maxqueuehead :
                self.h[ hdr.islno ]  = 0
            else :
                self.h[ hdr.islno ] += 1
            
            # Wake up any process that is waiting on the state of the queue
            self.cond.notify_all( )
        
        # Dropped out of with statement - queue lock has been released. But the
        # message counter memoryview remains. It refers to the shared memory,
        # which cannot close properly until this memoryview has been released.
        # We do it explicitly, in case the object is not destroyed through
        # garbage collection before the .close method is invoked.
        hmsg.release( )
         
        
    def  pop ( self , block = False , timer = 0.5 , decode = True ) :
    
        '''
        pop ( block = False , timer = 0.5 , decode = True )
        
        Reads the next next unread message from the queue and returns the tuple
        ( sender , type , msg ) ... see append. If the sender or type string is
        found in the scrnsend or scrntype sets, respectively, then the message
        is skipped, and pop looks for the next unread message in the queue. If
        there are no unread and unscreened messages then None is returned,
        unless block is True.
        
        Then pop will wait until there is a new message to read. Pop will wait
        indefinitely if timer is None. Otherwise, timer can be a float that
        gives the number of seconds that pop will wait for. If the timer expires
        before an unread message becomes available then None will be returned.
        
        By default, messages are decoded from bytes to str with the default
        encoding. But if decode is False then the raw bytes are returned.
        '''
        
        # Get time at start of function call. We use this to subtract elapsed
        # time from repeated waits on the condition variable, if frequent
        # screened messages are appended to the queue by another instance.
        if  timer : tin = time( )
        
        # Read loop
        while  True :
        
            # Scan queue body for next unread message
            for  m in self._next( ) :
                
                # Unpack msg counters and index of 1st byte to follow them
                ( h , b ) = m
                
                # Accumulate message header byte strings into this list, here
                bstr = [ ]
                
                # At this point we have a message, but it might become screened
                try :
                    
                    # Message header strings, and corresponding screening sets
                    for  ( i , s )  in  zip( hdr.mcnti , self.scrns ) :
                        
                        # Read byte string from shared memory
                        read , b = self._read( b , h[ i ] )
                        
                        # This message has a header string that is screened
                        if  read in s : raise hdr.ScreenedMessage
                        
                        # Append newly read byte string to list
                        bstr.append( read )
                    
                # We found a message on the queue, but it is screened
                except  hdr.ScreenedMessage : ret = None
                
                # A genuine error has occurred, pass it on i.e. re-raise it
                except  Exception as err :
                    print( f'Unexpected {err=}, {type(err)=}' )
                    raise
                
                # Message found! Read message body. Build return tuple 
                # containing strings. Break for loop to skip its else statement.
                else :
                    bstr.append(  self._read( b , h[ hdr.ibody ] )[ 0 ]  )
                    ret = tuple( b.decode( ) for b in bstr ) if decode else \
                          tuple( bstr )
                    break
                
                # Screened or not, we must decrement the read counter and alert
                # anything else that is blocking on the condition variable, but
                # only after freeing queue memory if this was the last read.
                # Guarantee message memoryview is released.
                finally :
                    with  self.cond :
                        h[ hdr.iread ] -= 1 ;
                        if  not h[ hdr.iread ] : self._free( h )
                        self.cond.notify_all( )
                    h.release( )
            
            # No message was found by _next iterator, for loop drops here
            else : ret = None
            
            # Un-screened and un-read message was found. Return it in a tuple
            # with format: message ( sender , type , body ). None evaluates as
            # False.
            if  ret : return ret
            
            # No unscreened message was found, but we may block on new messages
            if  block :
                
                # How much time has passed since the call to pop( )?
                if  timer : dt = timer - ( time( ) - tin )
                else : dt = None
                
                # Block on the condition variable
                with  self.cond :
                
                  # The predicate returns true if there is a message before
                  # timeout
                  if  self.cond.wait_for( self._popred , dt ) : continue
            
            # We only get here if no message was found and any blocking timed
            # out
            return  None


