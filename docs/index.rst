.. pysyncq documentation master file, created by
   sphinx-quickstart on Wed Aug 16 19:03:45 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Python Synchronisation Queue
============================

**pysyncq** is a multiprocessing data structure that is implemented entirely in
Python, using only the standard library. It acts to coordinate the activity of
separate processes in two domains. Time and Data. Any process that connects to
such a queue is able to share and receive messages with all others. Unlike a
conventional queue, a message is not removed until it has been read by all
connected processes. And any message that is written by one process will be read
by all others. A process can wait on the queue for incoming messages from other
processes, or to write its own message. Hence, the queue can be used to obtain
a measure of synchronised behaviour.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   intro
   modules
   dev


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
