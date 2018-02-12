# openflexure_microscope_software
Python scripts to run the OpenFlexure Microscope

This collection of scripts is what I use to run the OpenFlexure microscope.  It is not yet a proper Python module, although it should be.

## Microscope control scripts
The ``openflexure_microscope`` folder contains the scripts I use to run the microscope.  These include a library for the stage, and another one with utility functions for running the camera.  There's also ``microscope_control.py`` for interactive control of the microscope.

## Characterisation scripts
The [``microscope_characterisation``](microscope_characterisation) folder contains scripts for measuring the resolution, distortion, and pixels-to-microns calibration.  These are intended to produce images you then analyse with the [USAF analysis scripts](https://github.com/rwb27/usaf_analysis).

## Usage
Currently all these scripts live in one folder on my Pi - not in two folders as in this repository.  I'm working on organising them better...
