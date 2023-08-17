
'''
A simple demonstration of how pysyncq can be used to coordinate the behaviour of
multiple child processes. Program can be run from the command line:

e.g. $ python demo.py
'''


#--- Import block ---#

# Standard library
import multiprocessing as mp
import time as t
import random as rnd
import sys
from math import pi
from select import select

# pysyncq
from pysyncq import pysyncq as pq


#--- Global variables ---#

# Sets of grammatical elements
determiner = { 'a' , 'the' , 'your' , 'my' , "someone's" , "no one's" }
noun = { 'dog' , 'cat' , 'computer' , 'castle' , 'pear' , 'shire' , 'nose' }
verb = { 'ate' , 'married' , 'fled' , 'hid' , 'shared' , 'worried', 'satisfied'}

# Cast sets as tuples for random selection
tdet  = tuple( determiner )
tnoun = tuple( noun )
tverb = tuple( verb )


#--- Child process function ---#

def  cfun ( q , name ) :
    
    # Local copy of the queue must be opened to register the child process. A
    # name is provided that will identify who created each message.
    q.open( name )
    
    # Flush buffers to get immediate output to stdout
    print( name , 'opened' , q , flush = True )
    
    # Block indefinitely on a start signal from the parent process
    ( sender , msgtype , msg ) = q.pop( block = True , timer = None )
    
    # Check that this was the user's start signal from the parent process
    if ( sender , msgtype , msg ) != ( 'parent' , 'user' , 'start' ) :
    
        printf( f'{ name } received improper start signal.' , flush = True )
        
    else : print( name , 'received start signal.' )
    
    # Read flag is lowered when stop signal received
    rdflag = True
    
    # Read loop
    while  rdflag :
    
        # Random wait to simulate processing of some sort
        t.sleep( rnd.uniform( 0.01 , pi ) )
        
        # Build a sentence
        msg = [ rnd.choice( tdet ).capitalize( ) , rnd.choice( tnoun ) ,
                rnd.choice( tverb ) ]
        msg.append( rnd.choice( tuple( determiner - { msg[ 0 ] } ) ) )
        msg.append( rnd.choice( tuple(       noun - { msg[ 1 ] } ) ) )
        msg = ' '.join( msg ) + '.'
        
        # Add sentence to the tail of the queue. Wait briefly for free space.
        # Otherwise, abort the write.
        try :
          
            # Arg order is message type , message body. Waits 0.5sec by default.
            q.append( 'sentence' , msg , block = True )
          
        # The queue was full and no messages were removed from the head of the
        # queue before the write timer expired.
        except  MemoryError :
            
            print( f'{ name } aborts write due to full queue.' , flush = True )
        
    
        # Iterator behaviour, a timed wait for incoming messages
        for  m in q( block = True , timer = 0.2 ) :
            
            # Respond to different message types
            match m :
            
                # Check for stop signal. Lower flag to break read loop.
                case [ 'parent' , 'user' , 'stop' ] :

                    print( name , 'received stop signal.' , flush = True )
                    rdflag = False
                    break
                
                # Sentence received from another child process
                case [ _ , 'sentence' , msg ] :
                
                    print( name, f'read: "{ msg }" from', m[ 0 ], flush = True )
            
        # No messages returned before read timer expired.
        else :
        
            print( name , 'read timer expired.' , flush = True )
    
    # Always close the buffer. Last to close also unlinks shared memory.
    # Otherwise, shared memory is not released by the operating system, leaking
    # resources.
    q.close( )


#--- MAIN ---#

if __name__ == "__main__" :

    # Create a new synchronisation queue with a small buffer of shared memory
    q = pq.PySyncQ( 'pqdemo' , size = 256 )

    # Create one child per processor. NOTE that q is an input argument for the
    # child target function. This shares the same lock amongst the child
    # processes.
    P = [ mp.Process( target = cfun , args = ( q , f'Child-{i}' ) )
          for i in range( mp.cpu_count( ) ) ]

    # User triggers execution of child processes
    input( 'Hit <ENTER> to run child processes.' )

    # Start child process execution
    for p in P : p.start( )

    # Open local copy of the queue. Sender name is specified as 'parent'.
    # Default behaviour is to screen one's own messages, but this can be
    # disabled. See the filtself input argument.
    q.open( 'parent' )

    # User sends start signal
    t.sleep( 0.1 )
    input( 'Hit <ENTER> to send start signal.\n'
           'Hit <ENTER> again to send stop signal.' )

    # We append messages to the queue. Sender name is automatically included.
    # Here, the message type is 'user' and the message body is 'start'
    q.append( msgtype = 'user' , msg = 'start' )

    # Read loop
    while  True :

        # Wait for user input, one second at a time
        r , _ , _ = select( [ sys.stdin ] , [ ] , [ ] , 1 )
        
        # User hit enter
        if  r : break
        
        # Clear queue
        for  m in q : pass

    # Stop signal
    q.append( 'user' , 'stop' , block = True , timer = 30 )

    # Join terminated child processes
    for p in P : p.join( ) ; print( f'Joined pid { p.pid }.' , flush = True )

    # Close synchronisation queue
    q.close( )


