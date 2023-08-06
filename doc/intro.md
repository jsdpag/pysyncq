
# Introduction to pysyncq


# Developer notes

Shared memory is organised as follows

[ Queue header , Message 1 , Message 2 , ... ]

The queue header has the format:

[ processes , free bytes , head , tail ]

where each element is a separate counter with the following jobs:

*processes - Count the number of processes that are connected to the queue.
*free bytes - Number of bytes available in the queue for new messages.
*head - Locates the location where the next message will be written.
*tail - Locates the oldest message in the queue.

