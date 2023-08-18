
Get started with pysyncq
========================

Initialisation
--------------

A parent process must create a synchronisation queue first::

    q = PySyncQ( 'name_of_shared_memory' )
    
Then child processes can be created. The target function that they will execute
must accept at least one input argument, the queue object::

    def  child_target_function ( q ) :

The parent process may then create each child process, e.g. one per processor::

    import multiprocessing as mp
    
    P = [ mp.Process( target = child_target_function , args = ( q , ) )
          for i in range( mp.cpu_count( ) ) ]

The child processes must be forked from the parent using the start( ) method::

    for p in P : p.start( )

Once the child processes are forked, it is mandatory for each process to
register with the queue by opening its own copy of the PySyncQ instance::

    q.open( 'sender_name' )

This sequence of events will essentially achieve the following:

1) Register shared memory on the file system and create the memory-protection
   locks that are necessary for safe reading and writing to and from multiple
   processes.
2) Passing the PySyncQ instance as an input argument to each child will carry a
   copy of the memory-protection locks to each child process, once it is forked
   via the start( ) method.
3) Tell the queue how many processes are connected. Thus, how many reads must
   be performed on each message before it is removed from the queue. And how
   many processes must close the queue before unlinking the shared memory from
   the file system.

It may be advisable to allow child processes enough time to run the open( )
method on their copy of the PySyncQ object e.g.::

    import time
    time.sleep( 0.1 )

Sending messages
----------------

Write a new message to the tail of the queue::

    q.append( 'type_of_message' , 'The body of the message.' )
    
The name of the sender (given by the open method) is automatically added to the
message. The message type and body default to empty strings.

If the queue is too full then the default behaviour is to raise a MemoryError
exception. Catch this and handle the situation accordingly to prevent crashing
the program::

    try :
        q.append( 'mtype' , 'message body' )
      
    except  MemoryError :
        **Respond to lack of memory in queue**

Alternativley, one may block on the queue. That is, wait for enough space in the
queue to become freed::

    q.append( 'mtype' , 'message body' , block = True , timer = None )

If timer is None then the wait is not timed. The process will wait indefinitely
for enough space to write the message. But, if a timer duration is provided then
a write that blocks on the queue will fail with a MemoryError exception if the
timer expires::

    q.append( 'mtype' , 'message body' , block = True , timer = 3.14 )

The timer is given in seconds. It defaults to 0.5 second.

Either str or bytes objects can be written directly to the queue. But any object
**obj** that can be cast as str by str(**obj**) may be given as either the
message type or body. Be aware that it will be read out as a str that must be
parsed to extract any futher data types.

Reading messages
----------------

Read, or pop, the next message from the head of the queue::

    ( sender , mtype , mbody ) = q.pop( )

The message sender, type, and body are returned in a tuple. But, if there are
no unread messages then None is returned.

Messages can be screened, or filtered, by their sender and or their type. To do
this, add values to the PySyncQ object's attributes .scrnsend and .scrntype,
respectively. Both of these are sets. By default, each process ads its own
sender name to the .scrnsend set when the open( ) method is called. But this
can be disabled by q.open( filtself = False ). Or, the sender name can be
removed from the .scrnsend set.

If there are no unread messages then pop can block on the queue, to wait for
one::

    msgtuple = q.pop( block = True , timer = None )

As with .append( ), giving a timer value of None will result in an indefinite
wait. While providing a timer value in seconds will cause the wait to end when
the timer expires. An expired wait with no new message results in None to be
returned.

The messages are stored in the shared memory as byte strings. The raw bytes can
be returned by::

   msgbytestuple = q.pop( decode = False )
   
Be default, bytes are decoded back into str.

A PySyncQ instance can be treated as an iterator::

    for m in q :
        **Handle message m**
    else :
        **No more messages**

Each iteration of the for loop pops one more message from the queue until there
are no more unread messages.

By default, pop uses non-blocking reads. It does not wait for new messages if
there are none. But the waiting/blocking behaviour of the pop iterator can be
set::

    for m in q( block = True , timer = 0.123 ) :
        **Handle message m**
    else :
        **No more messages**

Likewise, the decode argument can be provided to return byte strings from the
PySyncQ iterator.

Closing and unlinking
---------------------

It is important for each process to release the queue before terminating::

    q.close( )

The queue maintains a count in shared memory of how many processes are still
connected. Once this number is decreased to zero then the associated shared
memory is unlinked from the file system.

General queue behaviour
-----------------------

The queue adds new messages from any process to the tail. But each process must
read each message, and maintains its own read position. So, processes may read
messages at different rates, and different times. The queue will remove a
message from the head of the queue only when it has been read by all connected
processes. This is a vital step for freeing unused memory where new messages may
be written. It is therefore good practice to ensure that each process reads
from the queue on some regular basis. At the very least, a process can mark all
queued messages as read without actually reading them::

    for m in q : pass

Although the queue allows for indefinite waits to read or write messages, it is
advisable to always set a timer. Unless there is good reason to. Otherwise, it
can be very easy for the program to freeze for ever.

Because the memory-protection locks must be passed as input arguments to the
child target function, it is unclear whether this is supported without forking.
Unix operating systems provide forking. But Windows will spawn child processes.
The difference being that forked processes retain all information available to
the parent process. While data must be pickled if it is to be preserved through
a spawn. At the time of writing, memory locking primatives cannot be pickled.

