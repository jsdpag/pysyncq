Developer notes
===============

Organisation of shared memory
-----------------------------

Shared memory is organised with a queue header followed by a queue body::

    [ Queue header ][ Queue body ]
    [ Header counters ][ Message 1 , Message 2 , ... ]

The queue header counters are a block of values::

    [ processes , free bytes , head , tail, write serial number ]

where each element is a separate counter with the following jobs:

* processes - Count the number of processes that are connected to the queue.
* free bytes - Number of bytes available in the queue for new messages.
* head - Locates the location where the next message will be written.
* tail - Locates the oldest message in the queue.
* write serial number - Each message written to the queue, no matter which
  process writes it, increments the serial number counter.

Queue counters are implemented with a relatively large integer type.
See header.py fmtqueuehead. As of v0.0.0 this is an unsigned long long,
or 64-bit integer on a standard Linux distribution. Hence, the counters
could overflow. But only under rather unusual circumstances.

Likewise, each message written to the queue has the organisation::

    [ Message header ][ Byte strings ]
    [ Message header counters ][ sender , message type , message body ]
    
With the following functions:

* header counters - See below.
* sender - Byte string identifying process that wrote the message.
* type - Byte string giving the type of message.
* body - The main contents of the message.
    
sender, type, and body are byte strings encoded from strings using the
default encoding format e.g. UTF-8.
    
Counters are a block of values::

    [ reads , sender bytes , type bytes , body bytes ]

* reads - Number of reads remaining on this message. The number is
  decremented once for each process that reads the message. When this
  is reduced to zero then the queue head jumps to the next message,
  and space is freed.
* sender, type, body - The number of bytes in each byte string.
    
Counters are in a slightly smaller integer type e.g. unsigned 32-bit integer.


Circular buffering of messages
------------------------------

One problem is that the message header counters require a contiguous block of
bytes. But messages can be any length that will fit within the availbe space of
the queue. Therefore, the end of one message may not leave enough space between
itself and the end of the queue body. Under these circumstances, the read or
write position, the queue head or tail will skip the trailing bytes and jump
back to the first byte of the queue body.

This is not an issue when a contiguous block of bytes do fit before the end of
the queue body. If the byte strings are too long to fit, then these are simply
wrapped around to the head of the queue body, like in a circular buffer.

For instance, a conventional message may be written in one stretch::

    [Queue header][Queue body]
    [Queue header][ ... , (Headers)(Bytes) , ... ]
    
Close to the end of the queue body, it may be necessary to wrap the byte
strings. Say that a message with length N byte strings is written with the
message counters M bytes from the end of the queue body::

    [Queue header][ (Bytes M+1 to N) , ... , (Headers)(Bytes 1 to M) ]

Thus, reading will first take the M bytes near the end of the body and
concatenate the N - M bytes from the start::

    (Bytes 1 to M)(Bytes M+1 to N) = [N bytes in correct order]

Any time that there are not enough bytes for a set of message header counters,
then the message will start from the beginning of the queue body::

    [Queue header][(New message) , ... (Old message) , (K bytes skipped) ]
    
Where K < length of message header.


Current design limitations
--------------------------

At the time of writing v0.0.0 of pysyncq, Python v3.11 is current. The
synchronisation primitives can only apparently be shared with another process
if it is inherited through a process fork. This is rather unlike POSIX, which
allows synchronisation primitives to be stored in shared memory that is linked
to the file system. Therefore, the mutex and condition variable must be created
by a parent process and then shared with child processes.


Message write and read Serial Numbers
-------------------------------------

To make full use of the queue body, it can happen that the queue head and tail
positions sit on the same byte. This is the case for a newly created and empty
queue, with both positions at byte zero. It can also the case if the queue
fills up and the tail wraps around to zero before any messages are removed from
the head. If the read position for an instance of the PySyncQ object also sits
on the same byte then it impossible to know whether the message(s) in the queue
have alread been read by the PySyncQ instance.

Serial numbers can solve this problem. If a separate number is assigned to each
read and to each write, then one need only to compare the read serial number
of the PySyncQ instance with the write serial number that is kept in the queue.

The queue header maintains the serial number of the most recent written message.
Serial numbers increment by +1 for each new message. If the counter ever
overflows then it is reset to 0. This may happen because the counter is
maintained by a fixed number of bytes in the shared memory queue header.

By contrast, each copy of the PySyncQ instance that is passed to the child
processes will maintain its own message read serial number. In a similar manner,
this is the number of the most recent read. And the number increments by +1 for
each new read. Although this is a Python int, it will also be reset to 0 when it
tries to exceed the maximum value of a queue header counter.

A logical error is theoretically possible if there is a large enough queue so
that at least one child process never reads any messages until enough have been
written to overflow the write serial number counter back to 0, and to wrap the
queue tail back around to the head. Now the instance read position, queue head
and tail, and the queue write and instance read serial numbers will all be the
same. Reads from the queue by the PySyncQ instance will fail, because this
situation will be interpreted as though that instance had actually read all of
the buffered messages, due to the fact that the read and tail positions are the
same, as are the read and write serial numbers.

While theoretically possible, it seems unlikely that this should ever occur in
practice. Highly unlikely. If the queue header counters are unsigned 64-bit
integers, then these can count up to 2 ** 64 - 1 = 18446744073709551615. That
many messages plus 1 must be written to trigger the logical error. For that to
happen, the queue must be large enough to contain that many message headers.
A minimalist message can have no sender, type, or body string. Only counters.
With four, four byte counters, each message requires 16 bytes. And with five,
eight byte counters, the queue header requires 40 bytes. Thus, at least 40 +
16 * 2 ** 64 = 295,147,905,179,352,825,896 bytes could be required.

Any consumer grade computers will be unable to maintain queues of that size over
the foreseeable future. While good practice will ensure that processes read
messages at some reasonable rate. Thus, either the serial numbers will not
overflow in most scenarios. Or, if the do, then the write number will never
race around and catch up with the read.

