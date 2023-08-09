
'''
Collects important constants together into a common namespace.
'''

#--- IMPORT BLOCK ---#

import  resource
from ctypes import c_ulong , c_ulonglong , sizeof


#--- GLOBALS ---#

# Page size in memory e.g. 4096 bytes.
# Default size of the shared memory.
defsize = resource.getpagesize( )

# Format string of numeric type used for counting. Unsigned long long.
# See https://docs.python.org/3/library/struct.html#module-struct
fmtqueuehead = 'Q'

# Format string of message-header counter. Unsigned long.
fmtmsghead = 'L'

# Number of bytes in one Unsigned long long. And one Unsigned long.
nbytequeuehead = sizeof( c_ulonglong )
nbytemsghead   = sizeof( c_ulong     )

# Number of counters in queue header [ processes , free bytes , head , tail ]
lenqueuehead = 4

# And number of counters in message header, all in bytes except reads
# [ reads , sender string , type string , message body ]
lenmsghead = 4

# Size of queue and message headers, in bytes
sizequeuehead = lenqueuehead * nbytequeuehead
sizemsghead   =   lenmsghead * nbytemsghead

# Ordinal index of each queue header counter with symbolic name
iproc = 0
ifree = 1
ihead = 2
itail = 3

# Ordinal index of each message header counter with symbolic name
iread = 0
isend = 1
itype = 2
ibody = 3 


