openflexure_microscope_software
===============================
Python module to run the OpenFlexure Microscope

This repository contains the scripts that run the openflexure microscope.  The bulk of the useful code is contained in the Python module ``openflexure_microscope``, though there are some control scripts for characterisation experiments that currently live in a separate folder.  These will be integrated into the main control program in due course.

Installation
------------
These scripts currently depend on a few things that aren't included in standard Raspbian and aren't easily installed with pip.  First, you need to install the updated `userland libraries <https://github.com/raspberrypi/userland>`_.  The simplest option is to download and compile - this takes around 15 mins on my Pi 3::

   git clone https://github.com/raspberrypi/userland.git
   cd userland
   ./buildme
   cd ..
   
After installing userland, you need to install `my fork of picamera <https://github.com/rwb27/picamera/tree/lens-shading>`_::

   git clone https://github.com/rwb27/picamera.git
   cd picamera
   git checkout lens-shading
   python setup.py install
   cd ..
   
If you get a permissions error, it may be that you need to prefix the ``python setup.py install`` line with ``sudo`` or perhaps adjust your Python install location.

After installing these libraries, you can install this software the same way::

   git clone https://github.com/rwb27/openflexure_microscope_software.git
   cd openflexure_microscope_software
   python setup.py install
   
This will automatically download and install the `libraries for the stage <https://github.com/rwb27/openflexure_nano_motor_controller>`_ via pip.  Once you have installed the module, you can run an interactive microscope control program by running the command ``openflexure_microscope`` in the terminal.

Usage
-----
The module installs a command-line script.  Run ``openflexure_microscope`` to start an interactive control program, or ``openflexure_microscope help`` to see options.

Development
-----------
If you want to be able to modify the scripts, instead of installing with ``python setup.py install``, use ``python setup.py develop``.  This leaves the scripts in the folder where they have been downloaded, but still links them into your system's Python path.  That will allow you to run them as normal, but makes them easier to edit.  Don't forget to commit your changes to Github - this may be easier if you first fork the repository on Github, then clone and install your copy of it.  This is relatively simple: first, click the "fork" button at the top right of this repository's page - that will create a repository in your account.  Next, go to that repository, and copy the URL from the "clone or download" link.  It should look like ``https://github.com/your_username/openflexure_microscope_software.git``.  Then, replace my URL with yours, and run the same commands::

   git clone https://github.com/your_username/openflexure_microscope_software.git
   cd openflexure_microscope_software
   python setup.py develop

Characterisation scripts
------------------------
The `microscope_characterisation folder <./microscope_characterisation>`_ contains scripts for measuring the resolution, distortion, and pixels-to-microns calibration.  These are intended to produce images you then analyse with the [USAF analysis scripts](https://github.com/rwb27/usaf_analysis).

