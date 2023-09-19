
'''
Install the Python Synchronisation Queue - pysyncqpip
'''

from setuptools import setup , find_packages
from pathlib import Path

# read the contents of your README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Setup parameters.
setup(  name = 'pysyncq' ,
     version = '0.0.1' ,
 description = 'Coordinate state & timing of multiple processes.' ,
         url = 'https://github.com/jsdpag/pysyncq' ,
      author = 'Jackson Smith' ,
     license = 'GPL' ,
   packages = find_packages( ) ,
   zip_safe = False ,
   long_description=long_description,
   long_description_content_type='text/markdown'
    )

