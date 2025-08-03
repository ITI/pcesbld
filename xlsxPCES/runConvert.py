
# this script requires python 3.10 or later to be called when the command 'python3' is
# passed through the subprocess command (for the 'match' statement).
# It needs the pandas and openpyxl packages to be installed
#
import pandas as pd
import subprocess
import argparse
import tempfile
import sys
import pdb
import os
import yaml
import json
import glob
import shutil

converted_files = []

script_present = {}

csvDir = ""
yamlDir = ""
descDir = ""
workingDir = ""
convertDir = ""
templateDir = ""
argsDir = ""

sheetNames = []

def normalizeSheetName(name):
    if name == 'execTime':
        return 'exec'

    if name == 'netParams':
        return 'netparams'

    return name

def convert_xlsx_to_csv(xlsx_file):
    """Converts all sheets in an XLSX file to individual CSV files."""

    # Read the Excel file
    xls = pd.ExcelFile(xlsx_file)

    # Iterate over each sheet
    for sheet_name in xls.sheet_names:

        # Read the sheet into a DataFrame
        df = pd.read_excel(xlsx_file, sheet_name=sheet_name)

        sheet_name = normalizeSheetName(sheet_name)
        sheetNames.append(sheet_name) 

        sheet_output_name = os.path.join(templateDir, sheet_name+"-sheet")
        # Create a CSV filename for the sheet
        csv_file = f"{sheet_output_name}.csv"
       
        # Write the DataFrame to a CSV file
        df.to_csv(csv_file, index=False)

        print(f"Sheet '{sheet_name}' converted to '{csv_file}'")
        converted_files.append(sheet_output_name)

    # if ipmap is not in xls.sheet_names we create an empty csv file for it
    if 'ipmap' not in xls.sheet_names:
        ipmap_name = os.path.join(templateDir, "ipmap-sheet.csv")
        with open(ipmap_name,'w') as wf:
            wf.write("Unnamed: 0,Unnamed: 1,Unnamed: 2,Unnamed: 3,Unnamed: 4,Unnamed: 5,Unnamed: 6")
            wf.write(",,,,,,")

def main():
    global workingDir, csvDir, templateDir, script_present, yamlDir, descDir, convertDir, argsDir 

    parser = argparse.ArgumentParser()
    parser.add_argument(u'-name', metavar = u'name of system', dest=u'name', required=True)
    parser.add_argument(u'-workingDir', metavar = u'working directory', dest=u'workingDir', required=True)
    parser.add_argument(u'-convertDir', metavar = u'directory with converter function', dest=u'convertDir', required=False)
    parser.add_argument(u'-xlsx', metavar = u'input file name', dest=u'xlsx', required=True)
    parser.add_argument(u'-csvDir', metavar = u'directory where csv file is found', dest=u'csvDir', required=True)
    parser.add_argument(u'-argsDir', metavar = u'directory where argument files are found', dest=u'argsDir', required=False)

    parser.add_argument(u'-templateDir', metavar = u'directory where csv templates (with symbols) are found', 
            dest=u'templateDir', required=True)

    parser.add_argument(u'-yamlDir', metavar = u'directory where results are stored', dest=u'yamlDir', required=True)
    parser.add_argument(u'-descDir', metavar = u'directory where auxilary descriptions are stored', dest=u'descDir', required=True)

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
    templateDir = args.templateDir

    scriptDir = os.path.dirname(__file__)

    if args.convertDir is None:
        convertDir = os.path.join(scriptDir, 'convert')
    else:
        convertDir = args.convertDir

    if args.argsDir is None:
        argsDir = os.path.join(convertDir, 'args')
    else:
        argsDir = args.argsDir

    commonDir = (csvDir, yamlDir, descDir, convertDir, argsDir, templateDir)
    commonDict = {'cp': csvDir, 'yamlDir': yamlDir, 'workingDir': workingDir, 
        'descDir': descDir, 'convertDir': convertDir, 'argsDir':argsDir, 'templateDir':templateDir}

    # ensure that these directories exist and are accessible
    errs = 0
    tempdirs = []
    required = ('yamlDir', 'convertDir', 'argsDir')
    for cd, cdir in commonDict.items():
        if not os.path.isdir(cdir):
            if cd not in required:
                commonDict[cd] = tempfile.mkdtemp() 
                print('{} argument directory {} not accessible, creating temporary directory {}'.format(__file__, 
                    cd, commonDict[cd]), file=sys.stderr)
                tempdirs.append(commonDict[cd])
            else:
                print(__file__, 'directory', cd, 'not accessible and is required', file=sys.stderr)
                exit(1)

    csvDir = commonDict['cp']
    descDir = commonDict['descDir']
    templateDir = commonDict['templateDir']
    workingDir = commonDict['workingDir']

    fileTypes = ('cp', 'topo', 'mapping', 'ipmap', 'netparams', 'exec', 'experiments')
    optional = ('experiments','ipmap')

    # make sure that the scripts expected for conversion are present
    
    for ft in fileTypes:
        script = os.path.join(convertDir, 'convert-'+ft+'.py')
        in_args = os.path.join(argsDir, 'args-'+ft)

        script_present[ft] = False
        if ft not in optional and not os.path.isfile(script):
            print("script {} expected but not found".format(script))
            errs += 1
        elif os.path.isfile(script):
            script_present[ft] = True

        if script_present[ft] and not os.path.isfile(in_args):
            print("argument file {} expected but not found".format(in_args))
            errs += 1

    if errs > 0:
        exit(1)

    for ft in fileTypes:

        if not script_present[ft]:
            continue

        in_args = os.path.join(argsDir, 'args-'+ft)
        out_args = os.path.join(workingDir,'args-'+ft)

        with open(in_args, 'r') as rf:
            with open(out_args, 'w') as wf:

                # write out common directories
                print('-csvDir {}'.format(csvDir), file=wf)
                print('-yamlDir {}'.format(yamlDir), file=wf)
                print('-descDir {}'.format(descDir), file=wf)
                print('-name {}'.format(name), file=wf)
                print('-validate', file=wf)
 
                for line in rf:
                    if line.startswith('#'):
                        continue
                    line = line.strip()
                    orgLine = line

                    pieces = line.split()

                    if not pieces[0].startswith('-'):
                        print('unexpected format of input file ',in_args)
                        exit(1)

                    if pieces[0] == '-csvDir':
                        print('-csvDir', csvDir, file=wf)
                    elif pieces[0] == '-yamlDir':
                        print('-yamlDir', yamlDir, file=wf)
                    elif pieces[0] == '-descDir':
                        print('-descDir', descDir, file=wf)
                    elif pieces[0] == '-name':
                        continue
                    else:
                        print(orgLine, file=wf) 


    xlsx_file = args.xlsx  # Replace with your file path
    convert_xlsx_to_csv(xlsx_file)

    # csv files are in templateDir.  Copy them all to csvDir
    template2csv()     

    # make sure we can get to all the files we expect in template

    # convert experiments sheet to get yaml output description
    transformations = [("convert-experiments.py", "experiments")] 

    for scriptName, sheet in transformations:
        convertSheet(scriptName, sheet, True)

    # the experiment yaml is in yamlDir
    experiment_input_file = os.path.join(yamlDir, 'experiments.yaml')
    with open(experiment_input_file, 'r') as rf:
        exprmnts = yaml.safe_load(rf)
   
    # make a map of the symbols to apply to each sheet
    sheet2symbol = {}
    example = exprmnts[0]
    expKeys = example.keys()

    for code in expKeys:
        if code=='name' or len(code)==0:
            continue

        pieces = code.split(',')
        if len(pieces) > 1:
            sheets = pieces[1:]
        else:
            sheets = sheetNames
        
        for sheet in sheets:
            sheet = sheet.strip()
            if sheet not in sheet2symbol:
                sheet2symbol[sheet] = []
            sheet2symbol[sheet].append(pieces[0].strip())
        
    # for each experiment copy the files to be modified from templateDir to csvDir and 
    # apply the transformations

    for exprmnt in exprmnts:
    
        exprmntName = exprmnt['name']
        print('validating experiment {}'.format(exprmntName))

        # copy the files to be modified
        for sheet in sheet2symbol:
            templateFile = os.path.join(templateDir, sheet+'-sheet.csv')
            inputFile = os.path.join(csvDir, sheet+'-sheet.csv')
            shutil.copyfile(templateFile, inputFile)
 
        remap = {}
        for code, value in exprmnt.items():
            value = str(value)
            if code == 'name' or len(code) == 0:
                continue
            pieces = code.split(',')
            token = pieces[0].strip()
            remap[token] = value 

        for sheet, symbolList in sheet2symbol.items():
            inputFile = os.path.join(csvDir, sheet+'-sheet.csv')
            tmpFile = os.path.join(csvDir, 'tmp-'+sheet+'-sheet.csv')

            with open(inputFile, 'r') as rf:
                with open(tmpFile, 'w') as wf:
                    for line in rf:
                        for symbol, value in remap.items():
                            if line.find(symbol) > -1:
                                strSymbol = 'str('+symbol+')'
                                if line.find(strSymbol) > -1:
                                    #valueStr = '"'+value+'"'
                                    valueStr = value
                                    line = line.replace(strSymbol, valueStr)
                                    continue
                                intSymbol = 'int('+symbol+')'
                                if line.find(intSymbol) > -1:
                                    line = line.replace(intSymbol, str(value))
                                    continue
 
                                boolSymbol = 'bool('+symbol+')'
                                if line.find(boolSymbol) > -1:
                                    line = line.replace(boolSymbol, str(boolRep(value)))
                                    continue
 
                                floatSymbol = 'float('+symbol+')'
                                if line.find(floatSymbol) > -1:
                                    line = line.replace(floatSymbol, str(value))
                                    continue
 
                        wf.write(line)

            # move the copied version back
            shutil.copyfile(tmpFile, inputFile)                 
            os.remove(tmpFile)

        # check ALL files for symbols
        unresolved = {}
        for sheet in sheetNames:
            if sheet == 'experiments':
                continue
            inputFile = os.path.join(csvDir, sheet+'-sheet.csv')
            with open(inputFile, 'r') as rf:
                for line in rf:
                    if line.find('$') > -1 or line.find('@') > -1:
                        unresolved[sheet] = True
                        break

        if len(unresolved) > 0:
            sheets = unresolved.keys()
            print('undefined symbols in sheets {}'.format(sheets))
            exit(0)

        # all the symbol replacements are done, so convert all the sheets, (again)
        # N.B. a sheet that was modified may generate aux files that depend on the
        # modification, which means that downstream transformations depend on it, so
        # we broad-brush the conversions 
        transformations = [("convert-exec.py", "exec"), ("convert-topo.py", "topo"), 
            ("convert-ipmap.py", "ipmap"), ("convert-cp.py", "cp"),
            ("convert-map.py", "map"), ("convert-netparams.py", "netparams")]

        for scriptName, sheet in transformations:
            if sheet in sheetNames:
                convertSheet(scriptName, sheet, True)

        # errors that crop up due to individual experiments have been reported, now
        # do the transformation on the csvs that carry the symbols

    # copy all the templated files into csvDir for processing
    template2csv()

    # transformations w/o experiment sheet
    transformations = [("convert-exec.py", "exec"), ("convert-topo.py", "topo"), ("convert-cp.py", "cp"),
        ("convert-map.py", "map"), ("convert-ipmap.py", "ipmap"), ("convert-netparams.py", "netparams"), ("convert-experiments.py", "experiments")]

    # do 'em all
    print("Transform csv files with symbols to yaml files with symbols")
    for scriptName, sheet in transformations:
        if sheet in sheetNames:
            convertSheet(scriptName, sheet, False)

def template2csv():
    directory_path = templateDir
    file_pattern = '*.csv'
    filenames = glob.glob(f'{directory_path}/{file_pattern}')

    for filePath in filenames:
        basename = os.path.basename(filePath) 
        input_file = os.path.join(csvDir, basename)
        shutil.copyfile(filePath, input_file)            
    

def convertSheet(scriptName, sheet, validate):
    global convertDir, workingDir 
    if not script_present[sheet]:
        return 

    scriptPath = os.path.join(convertDir, scriptName)
    argsPath = os.path.join(workingDir, "args-"+sheet)
    argsPathV = os.path.join(workingDir, "args-"+sheet+'-v')

    with open(argsPathV, 'w') as wf:
        with open(argsPath, 'r') as rf:
            for line in rf:
                if line.find('-validate') > -1:
                    if not validate:
                        continue
                    wf.write('-validate\n')
                else:
                    wf.write(line)
 
    argsPath = argsPathV 

    process = subprocess.Popen(["python3", scriptPath, "-is", argsPath], 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
   
    if len(stdout) > 0:
        print(stdout)

    if len(stderr) > 0 :
        print(stderr)

    #if process.returncode != 0:

    #    print("Error from {}: {}".format(scriptName, stderr))
    #else:
    #    if len(stdout) > 0:
    #        print(stdout)

    #    if len(stderr) > 0 :
    #        print(stderr)

def boolRep(v):
    if isinstance(v,int):
        if v==0 or v==1:
            return v
        return 0

    if isinstance(v,str):
        if v in ('T', 'True', 'TRUE', 't', 'true', 'Y', 'Yes', 'YES', 'yes', '1'):
            return 1
        return 0



if __name__ == "__main__":
    main()


