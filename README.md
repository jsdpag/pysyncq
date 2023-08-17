
# Python Synchronisation Queue

This is a multiprocessing data structure that coordinates a
set of child processes in two senses.

1. Data - Any connected process can add data to the queue  
for all others to read.
2. Time - Processes can wait on the queue for new data to  
be added by any other. 

Every process that connects to the same queue is both a
reader and writer *i.e.* it is both a producer and a
consumer. But a piece of data is not removed from the
queue until every connected process has had a chance to
read it. Hence, one process can signal all of the others
to respond to the same information.

* See docs/_build/html/index.html for basic API documentation.
* See pysyncq/tests/demo.py for a simple demonstration of  
basic timing signals and message passing between processes.

