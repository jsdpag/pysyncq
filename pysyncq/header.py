
'''
Collects important constants together into a common namespace.
'''

#--- IMPORT BLOCK ---#

import  resource
from ctypes import c_ulonglong , sizeof


#--- GLOBALS ---#

# Page size in memory e.g. 4096 bytes.
# Default size of the shared memory.
defsize = resource.getpagesize( )

# Format string of numeric type used for counting. Unsigned long long.
# See https://docs.python.org/3/library/struct.html#module-struct
fmtcnt = 'Q'

# Number of bytes in one Unsigned long long.
numcnt = sizeof( c_ulonglong )

# Number of counters in queue header [ processes , free bytes , head , tail ]
numqh = 4

# Ordinal index of each queue header counter with symbolic name
iproc = 0
ifree = 1
ihead = 2
itail = 3

# Size of queue header, in bytes
sizeqh = numqh * numcnt


