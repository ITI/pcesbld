
# this script requires python 3.10 or later to be called when the command 'python3' is
# passed through the subprocess command (for the 'match' statement).
# It needs the pandas and openpyxl packages to be installed
#
import pandas as pd
import subprocess
import argparse
import sys
import pdb
import os

converted_files = []

workingDir = ''
full_csvDir = ''

def convert_xlsx_to_csv(xlsx_file):
    """Converts all sheets in an XLSX file to individual CSV files."""

    # Read the Excel file
    xls = pd.ExcelFile(xlsx_file)

    # Iterate over each sheet
    for sheet_name in xls.sheet_names:
        # Read the sheet into a DataFrame
        df = pd.read_excel(xlsx_file, sheet_name=sheet_name)

        sheet_output_name = os.path.join(full_csvDir, sheet_name+"-sheet")
        # Create a CSV filename for the sheet
        csv_file = f"{sheet_output_name}.csv"
       
        # Write the DataFrame to a CSV file
        df.to_csv(csv_file, index=False)

        print(f"Sheet '{sheet_name}' converted to '{csv_file}'")
        converted_files.append(sheet_output_name)

def main():
    global workingDir, full_csvDir

    parser = argparse.ArgumentParser()
    parser.add_argument(u'-name', metavar = u'name of system', dest=u'name', required=True)
    parser.add_argument(u'-workingDir', metavar = u'working directory', dest=u'workingDir', required=True)
    parser.add_argument(u'-convertDir', metavar = u'directory with converter function', dest=u'convertDir', required=True)
    parser.add_argument(u'-xlsx', metavar = u'input file name', dest=u'xlsx', required=True)
    parser.add_argument(u'-csvDir', metavar = u'directory where csv file is found', dest=u'csvDir', required=True)
    parser.add_argument(u'-yamlDir', metavar = u'directory where results are stored', dest=u'yamlDir', required=True)
    parser.add_argument(u'-descDir', metavar = u'directory where auxilary descriptions are stored', dest=u'descDir', required=True)
    parser.add_argument(u'-build', action='store_true', required=False)

    cmdline = sys.argv[1:]
    if len(sys.argv) == 3 and sys.argv[1] == "-is":
        cmdline = []
        with open(sys.argv[2],"r") as rf:
            for line in rf:
                line = line.strip()
                if len(line) == 0 or line.startswith('#'):
                    continue
                cmdline.extend(line.split()) 

    args = parser.parse_args(cmdline)

    name = args.name
    csvDir = args.csvDir
    yamlDir = args.yamlDir
    descDir = args.descDir
    workingDir = args.workingDir
    convertDir = args.convertDir

    full_csvDir = os.path.abspath(csvDir)
    full_yamlDir = os.path.abspath(yamlDir)
    full_descDir = os.path.abspath(descDir)
    full_convertDir = os.path.abspath(convertDir)     
    full_argsDir = os.path.join(full_convertDir, 'args')

    commonDir = (full_csvDir, full_yamlDir, full_descDir, full_convertDir, full_argsDir)

    # ensure that these directories exist and are accessible
    errs = 0
    for cd in commonDir:
        if not os.path.isdir(cd):
            print('argument directory', cd, 'not accessible')
            errs += 1

    if errs>0:
        exit(1)

    fileTypes = ('cp', 'topo', 'map', 'netparams', 'exec')
    # make sure that the scripts expected for conversion are present
    
    for ft in fileTypes:
        script = os.path.join(full_convertDir, 'convert-'+ft+'.py')
        in_args = os.path.join(full_argsDir, 'args-'+ft)

        if not os.path.isfile(script):
            print("script %s expected but not found".format(script))
            errs += 1

        if not os.path.isfile(in_args):
            print("argument file %s expected but not found".format(in_args))
            errs += 1

    if errs > 0:
        exit(1)


    for ft in fileTypes:
        in_args = os.path.join(full_argsDir, 'args-'+ft)
        out_args = os.path.join(workingDir,'args-'+ft)

        with open(in_args, 'r') as rf:
            with open(out_args, 'w') as wf:

                # write out common directories
                print('-csvDir {}'.format(full_csvDir), file=wf)
                print('-yamlDir {}'.format(full_yamlDir), file=wf)
                print('-descDir {}'.format(full_descDir), file=wf)
                print('-name {}'.format(name), file=wf)
 
                for line in rf:
                    if line.startswith('#'):
                        continue
                    line = line.strip()
                    orgLine = line

                    pieces = line.split()
                    if len(pieces) < 2:
                        continue
                    if not pieces[0].startswith('-'):
                        print('unexpected format of input file ',in_args)
                        exit(1)

                    if pieces[0] == '-csvDir':
                        print('-csvDir', full_csvDir, file=wf)
                    elif pieces[0] == '-yamlDir':
                        print('-yamlDir', full_yamlDir, file=wf)
                    elif pieces[0] == '-descDir':
                        print('-descDir', full_descDir, file=wf)
                    elif pieces[0] == '-name':
                        continue
                    else:
                        print(orgLine, file=wf) 


    xlsx_file = args.xlsx  # Replace with your file path
    convert_xlsx_to_csv(xlsx_file)

    if args.build:
        print('transforming execTime-sheet.csv to input files')

        transformations = [("convert-exec.py", "exec"), ("convert-topo.py", "topo"), ("convert-cp.py", "cp"),
            ("convert-map.py", "map"), ("convert-netparams.py", "netparams")]

        for scriptName, sheet in transformations:
            scriptPath = os.path.join(full_convertDir, scriptName)
            argsPath = os.path.join(workingDir, "args-"+sheet)

            process = subprocess.Popen(["python3", scriptPath, "-is", argsPath], 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
           
            if process.returncode != 0:
        
                print("Error from {}: {}".format(scriptName, stderr))
            else:
                if len(stderr) > 0 :
                    print(stderr)
                else:
                    print("ok", sheet)

if __name__ == "__main__":
    main()


