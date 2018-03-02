openflexure_microscope_software
===============================
Python module to run the OpenFlexure Microscope

This repository contains the scripts that run the openflexure microscope.  The bulk of the useful code is contained in the Python module ``openflexure_microscope``, though there are some control scripts for characterisation experiments that currently live in a separate folder.  These will be integrated into the main control program in due course.

Installation
------------
These scripts currently depend on a few things that aren't included in standard Raspbian and aren't easily installed with pip.  First, you need to install the updated `userland libraries <https://github.com/raspberrypi/userland>`_.  The simplest option is to download and compile - this takes around 15 mins on my Pi 3:

.. code-block:: bash
   git clone https://github.com/raspberrypi/userland.git
   cd userland
   ./buildme
   cd ..
   
After installing userland, you need to install `my fork of picamera <https://github.com/rwb27/picamera/tree/lens-shading>`_:

.. code-block:: bash
   git clone https://github.com/rwb27/picamera.git
   cd picamera
   git checkout lens-shading
   python setup.py install
   cd ..
   
If you get a permissions error, it may be that you need to prefix the ``python setup.py install`` line with ``sudo`` or perhaps adjust your Python install location.

After installing these libraries, you can install this software the same way:

.. code-block:: bash
   git clone https://github.com/rwb27/openflexure_microscope_software.git
   cd openflexure_microscope_software
   python setup.py install
   
This will automatically download and install the `libraries for the stage <https://github.com/rwb27/openflexure_nano_motor_controller>`_ via pip.  Once you have installed the module, you can run an interactive microscope control program by running the command ``openflexure_microscope`` in the terminal.

Usage
-----
The module installs a command-line script.  Run ``openflexure_microscope`` to start an interactive control program, or ``openflexure_microscope help`` to see options.

Characterisation scripts
------------------------
The `microscope_characterisation folder <./microscope_characterisation>`_ contains scripts for measuring the resolution, distortion, and pixels-to-microns calibration.  These are intended to produce images you then analyse with the [USAF analysis scripts](https://github.com/rwb27/usaf_analysis).

