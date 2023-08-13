
'''
Collects important constants together into a common namespace.
'''

#--- IMPORT BLOCK ---#

import  resource
from ctypes import c_uint , c_ulonglong , sizeof


#--- GLOBALS ---#

# Page size in memory e.g. 4096 bytes.
# Default size of the shared memory.
defsize = resource.getpagesize( )

# Format string of numeric type used for counting. Unsigned long long.
# See https://docs.python.org/3/library/struct.html#module-struct
fmtqueuehead = 'Q'

# Format string of message-header counter. Unsigned long.
fmtmsghead = 'I'

# Number of bytes in one Unsigned long long. And one Unsigned long.
nbytequeuehead = sizeof( c_ulonglong )
nbytemsghead   = sizeof( c_uint      )

# Max value of each counter type
maxqueuehead = 2 ** ( nbytequeuehead * 8 ) - 1
maxmsghead   = 2 ** ( nbytemsghead   * 8 ) - 1

# Number of counters in queue header:
#   [ processes , free bytes , head , tail , serial number ]
lenqueuehead = 5

# And number of counters in message header, all in bytes except reads
# [ reads , sender string , type string , message body ]
lenmsghead = 4

# Size of queue and message header counters, in bytes
sizequeuehead = lenqueuehead * nbytequeuehead
sizemsghead   =   lenmsghead * nbytemsghead

# Max size of shared memory is size of queue header + minimum length message
# size times max value of the queue header serial number counter. The smallest
# message has no sender, type, or body string; only message header counters.
maxshmemory = sizequeuehead + maxqueuehead * sizemsghead

# Ordinal index of each queue header counter with symbolic name
iproc = 0
ifree = 1
ihead = 2
itail = 3
islno = 4

# Ordinal index of each message header counter with symbolic name
iread = 0
isend = 1
itype = 2
ibody = 3

# Pack index for sender and type strings in a tuple for easy zipping
mcnti = ( isend , itype )


#--- EXCEPTIONS ---#

class  ScreenedMessage ( Exception ) :

    '''
    Used to signal when a message has been read from the queue and then screened
    from further use because the sender or type reside in the instance's screen
    sets.
    '''
    
    pass



