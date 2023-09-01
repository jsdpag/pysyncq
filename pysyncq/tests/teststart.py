
'''
Test a specified start method on a named test script. Two input args expected.
Start method and test script file name.
'''

#--- IMPORT BLOCK ---#

from sys import argv
import multiprocessing as mp
from runpy import run_path


#--- MAIN ---#

if  __name__ == '__main__' :

    # Name input args
    ( method , script ) = argv[ 1 : 3 ]
    
    # Set the start method
    mp.set_start_method( method )
    print( f"Start method method set to '{ mp.get_start_method( ) }'." )

    # Run named test script
    print( f'Executing {script}.' )
    run_path( script , run_name = '__main__' )

