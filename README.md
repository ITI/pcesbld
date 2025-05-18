[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

#### The xlsxPCES Tool

The pcesbld repository holds tools for creating pces model input files from an Excel spreadsheet.

The spreadsheet cells are text and values, and reference objects the user defines for the model as well as keywords referring to concepts in the pces model API.

The tools are python scripts that extract the sheets from the input .xlsx file and create .csv representations of those sheets.   Each sheet maps to one or two particular pces input files, and for each sheet there is a python script that analyzes the csv structure and creates corresponding .yaml input file(s) for pces.  The scripts do a considerable (but not yet completely exhaustive) amount of model expression validation, to protect pces and the user from run-time crashes that are due to mistakes in the model expression.

Subdirectory 'convert' holds the scripts for creating the the csv representation from xlsx, and for creating the pces input files.   Subdirectory 'examples' holds examples of input Excel spreadsheets, and subdirectory 'template' holds a template to use when building a new model.

python3.10 or later is needed, with the installation of pandas and openpyxl packages.



#### The PCES/MRNES System

The Patterned Computation Evaluation System (PCES) and Multi-resolution Network Emulator and Simulator (MRNES) are software frameworks one may use to model computations running on distributed system with the focus on estimating its performance and use of system resources.

The PCES/MRNES System is written in the Go language.  We have written a number of GitHub repositories that support this system, described below.

- https://github.com/iti/evt/vrtime .  Defines data structures and methods used to describe virtual time.
- https://github.com/iti/rngstream .  Implements a random number generator.
- https://github.com/iti/evt/evtq . Implements the priority queue used for event management.
- https://github.com/iti/evt/evtm . Implements the event manager.
- https://github.com/iti/evt/mrnes . Library of data structures and methods for describing a computer network.
- https://github.com/iti/evt/pces .  Library of data structures and methods for modeling patterned computations and running discrete-event simulations of those models.
- https://github.com/iti/evt/pcesbld . Repository of tool **xlsxPCES** used for describing PCES/MRNES models and generating input files used to run simulation experiments.
- https://github.com/iti/evt/pcesapps . Repository of PCES/MRNES example models, and scripts to generate and run experiments on those models.



Copyright 2025 Board of Trustees of the University of Illinois.
See [the license](LICENSE) for details.