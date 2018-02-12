__author__ = 'Richard Bowman'

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

version = "0.1.1"

setup(name = 'openflexure_microscope',
      version = version,
      description = 'Control scripts for the OpenFlexure Microscope',
      long_description = long_description,
      url = 'http://www.github.com/rwb27/openflexure_microscope_software',
      author = 'Richard Bowman',
      author_email = 'r.w.bowman@bath.ac.uk',
      download_url = 'https://github.com/rwb27/openflexure_microscope_software/archive/{}.tar.gz'.format(version),
      packages = find_packages(),
      keywords = ['arduino','serial','microscope'],
      zip_safe = True,
      classifiers = [
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Programming Language :: Python :: 2.7'
          ],
      install_requires = [
          'pyserial',
          'openflexure_stage',
          'picamera',
          'numpy',
          'scipy',
          'opencv',
          'matplotlib',
          ],
      )

