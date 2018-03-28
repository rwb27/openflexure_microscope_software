openflexure_microscope_software
===============================
Python module to run the OpenFlexure Microscope

This repository contains the scripts that run the openflexure microscope.  The bulk of the useful code is contained in the Python module ``openflexure_microscope``, though there are some control scripts for characterisation experiments that currently live in a separate folder.  These will be integrated into the main control program in due course.

Installation
------------
There are a few packages that are required in order to run the microscope module.  While the package metadata will mean that ``pip`` tries to install them, it's time consuming (and not always possible) to install everything from scratch on the Pi.  It is much easier to use the packaged versions of the relevant modules from Raspbian.  Connect your Pi to the internet, open a command prompt, and type::

   sudo apt-get install python python-numpy python-matplotlib python-scipy python-opencv python-picamera

You may already have these packages installed, in which case that's great!  The ``openflexure_microscope`` module can be installed using ``pip``.  Open a command prompt on your Raspberry Pi, and ensure it is connected to the internet.  Then type::

   sudo pip install https://github.com/rwb27/openflexure_microscope_software/archive/master.zip

This will, by default, ensure you have the dependencies installed, including ``picamera``.  This may have the unintended consequence of reverting to the official release of picamera; if you have previously installed my fork of picamera, you will need to reinstall it afterwards.  This will also automatically download and install the `libraries for the stage <https://github.com/rwb27/openflexure_nano_motor_controller>`_ via pip.

In order to use the advanced features (lens shading correction and full analog/digital gain control) you need to install both the latest firmware and my updated fork of ``picamera``.  Happily these are both now one-liners.  To use the latest firmware (strictly speaking it's the userland libraries that we need), run::

   sudo rpi-update stable
   
If you don't have ``rpi-update`` installed, you can get it by doing ``sudo apt-get install rpi-update`` on Raspbian.  This will install the latest firmware, you need to reboot in order to activate it.  Next, you need to install `my fork of picamera <https://github.com/rwb27/picamera/tree/lens-shading>`_::

   sudo pip install https://github.com/rwb27/picamera/archive/lens-shading.zip
   
Once you have installed the module, you can run an interactive microscope control program by running the command ``openflexure_microscope`` in the terminal.

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

