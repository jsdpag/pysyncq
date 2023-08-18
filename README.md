
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

PyPI package at [pypi.org/project/pysyncq](https://pypi.org/project/pysyncq/)

Online documentation at [pysyncq.readthedocs.io](https://pysyncq.readthedocs.io)

GitHub project at [github.com/jsdpag/pysyncq](https://github.com/jsdpag/pysyncq)

* See docs/_build/html/index.html for basic API documentation.
* See pysyncq/tests/demo.py for a simple demonstration of  
basic timing signals and message passing between processes.
* See pysyncq/tests/benchmark.py for a simple benchmarking of
the message transfer time from a sender to a reader.

Developed by:
* [Jackson Smith](https://www.linkedin.com/in/jackson-e-t-smith)

