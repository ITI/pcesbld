The pcesbld repository holds tools for creating pces model input files from an Excel spreadsheet.

The spreadsheet cells are text and values, and reference objects the user defines for the model as well as keywords referring to concepts in the pces model API.

The tools are python scripts that extract the sheets from the input .xlsx file and create .csv representations of those sheets.   Each sheet maps to one or two particular pces input files, and for each sheet there is a python script that analyzes the csv structure and creates corresponding .yaml input file(s) for pces.  The scripts do a considerable (but not yet completely exhaustive) amount of model expression validation, to protect pces and the user from run-time crashes that are due to mistakes in the model expression.

Subdirectory 'convert' holds the scripts for creating the the csv representation from xlsx, and for creating the pces input files.   Subdirectory 'examples' holds examples of input Excel spreadsheets, and subdirectory 'template' holds a template to use when building a new model.

python3.10 or later is needed, with the installation of pandas and openpyxl packages.