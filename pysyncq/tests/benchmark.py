
'''
Get a measure of the message transfer time from a source process to a reader
through a PySyncQ interface. Prints table in which the average and standard
error of the mean of the transfer times are given in milliseconds for a range of
message body sizes. Runs with 8 processes connected to one PySyncQ object.
'''


#--- Import block ---#

# Standard library
import gc , time
import          random as rnd
import      statistics as stat
import multiprocessing as mp

# pysyncq
from pysyncq import pysyncq as pq
from pysyncq import  header as hdr


#--- Globals ---#

# Largest message body size, given as the power of two i.e. 2 ** maxsize
maxsize = 16

# The total number of processes to create. 1 is parent and sender. The rest are
# child processes that echo the incoming message.
nprocs = 8

# Number of times to send/receive a given message per timing measurement. Set to
# one thousand, making the measured time duration equal to the average number
# of milliseconds that the operation took.
transfers = 1_000

# Number of samples to measure for the average ± SEM. Each sample times a run of
# transfers message send/receive cycles.
samples = 10

# Raise this flag to True to print each sample. Otherwise, keep it False.
samflg = False


#--- Child function ---#

def  cfun ( q , name ) :

    # Open queue and use given sender name
    q.open( name )
    
    # Filter all messages of type 'echo'
    q.scrntype.add( 'echo' )
    
    # We do not want automatic garbage collection to mess up timing
    gc.disable( )
    
    # Read loop. Wait indefinitely for new messages.
    for  ( _ , typ , msg )  in  q( block = True , timer = None ) :
        
        # Kill signal, terminate program
        if  typ == 'kill' : break
        
        # Force garbage collection
        if  typ == 'gc' : gc.collect( ) ; continue
        
        # Echo the message back to the queue
        q.append( 'echo' , msg , block = True , timer = None )
        
    # Release PySyncQ object
    q.close( )


#--- Message transfer timing function ---#

def  transtime ( q , msg , N ) :
    
    # Stop auto garbage collection during time measurement
    gc.disable( )
    
    # Measure start time
    tstart = time.time( )
    
    # Transfers
    for  i in range( N ) :
    
        # Send the message
        q.append( 'origin' , msg , block = True , timer = None )
        
        # Get the echo
        q.pop( block = True , timer = None )
        
        # Screen all others
        for _ in q : pass
    
    # Measure end time
    tend = time.time( )
    
    # Trigger garbage collection in all processes
    q.append( 'gc' )
    gc.collect( )
    gc.enable( )
    
    # Half the consumed time, subtracting out the echoed message
    dt = ( tend - tstart ) / 2.0
    
    # Individual samples
    if samflg : print( f'Sample: {dt} seconds' )
    
    # Return sampled time duration
    return  dt


#--- MAIN ---#

if __name__ == "__main__" :
    
    
    # Create new synchronisation queue. Request enough shared memory so that the
    # queue is unlikely to lack space for any write. We are chiefly interested
    # in transfer times under favourable conditions.
    q = pq.PySyncQ( name = 'transtime' , size = 10 * nprocs * 2 ** maxsize )
    
    # Create child process objects. Each with a copy of the queue, and a unique
    # message sender name.
    P = [ mp.Process( target = cfun , args = ( q , f'child-{ i }' ) )
          for i in range( nprocs - 1 ) ]
    
    # Start child process execution, so that parent process can ...
    for p in P : p.start( )
    
    # ... connect to the queue.
    q.open( 'parent' )
    
    # Brief wait so that child processes can all initialise
    time.sleep( 0.1 )
    
    # Parent process will ignore echoed messages from all but one child process.
    for i in range( 1 , nprocs - 1 ) : q.scrnsend.add( f'child-{ i }' )
    
    # Burn-in timer function
    transtime( q , bytes( 10 ) , 100 )
    
    # Table headers
    print( 'Msg bytes,Avg time (ms),SEM' )
    
    # Message sizes
    for p in range( 1 , maxsize + 1 ) :
    
        # Make message just once
        msg = bytes( 2 ** p )
        
        # Take numerous samples of the unidirectional transfer time
        X = [ transtime( q , msg , transfers ) for i in range( samples ) ]
        
        # The mean and SEM transfer time, in ms
        avg = stat.mean( X )
        sem = stat.stdev( X ) / samples ** 0.5
        
        # Show the result
        print( f'{2**p},{avg:.3},{sem:.3}' )
    
    # Send kill signal
    q.append( 'kill' )
    
    # Release queue resources
    q.close( )
    
    # Clean up terminated child processes
    for p in P : p.join( )
    
    
