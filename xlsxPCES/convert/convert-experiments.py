import sys
import os
import csv
import pdb
import yaml
import json
import argparse

# globals
cryptoOps = ('encrypt', 'decrypt', 'hash', 'sign')
cryptoAlgs = ('aes', 'rc6')
cryptoModes = ('ECB', 'CBC', 'CFB', 'OFB', 'CTR', 'XTS')
cryptoAEModes = ('CCM', 'GCM', 'CWC', 'EAX', 'IAPM', 'OCB')

expNameIdx = 0
variableName = []

sheetNames = ('topo', 'cp', 'execTime', 'mapping', 'netParams')

def cnvrtBool(v):
    if isinstance(v,int) and (v==0 or v==1):
        return v

    if isinstance(v,str):
        if v in ('T','True','TRUE', 'yes', 'YES', 'Y', 'y'):
            return 1
        if v in ('F','False', 'FALSE', 'no', 'NO', 'N', 'n'):
            return 0

    return v 

class ExperimentEntry:
    def __init__(self, row):
        self.name = row[expNameIdx]
        self.variableDict = {}
        for idx in range(1,len(variableName)+1):
            self.variableDict[ variableName[idx-1] ] = cnvrtBool("".join(row[idx].split()))

    def validate(self):
        msgs = []
        # ensure that every sheet referenced is recognized
        for variable in self.variableDict:
            if not isinstance(variable, str):
                continue
 
            pieces = variable.split(':')
            if len(pieces) > 1: 
                sheets = pieces[1:]
                for sheet in sheets:
                    if sheet not in sheetNames:
                        msgs.append('sheet name {} in value specification {} is not recognized'.format(sheet, variable))

        if len(msgs):
            return False, '\n'.join(msgs)
        return True, ""

    def equals(self, ee):
    
        for key, value in self.variableDict.items(): 
            if key not in ee.variableDict:
                return False
            if value != ee.variableDict[key]:
                return False

        for key, value in ee.variableDict.items(): 
            if key not in self.variableDict:
                return False
            if value != self.variableDict[key]:
                return False

        return True


    def repDict(self):
        rd = {'name': self.name}
        for key, value in self.variableDict.items():
            rd[key] = value

        return rd

def isCrypto(code):
    if code.find('-') == -1:
        return False
    fields = code.split('-')
    haveKeyLen = (fields[3].isdigit() and int(fields[3]) > 0)
    if fields[0] in cryptoOps and haveKeyLen:
        if not fields[1] in cryptoAlgs or not fields[2] in cryptoModes:
            return False
        return True

    return False

def comment(row):
    for cell in row:
        if cell.strip().startswith('#'):
            return True

    return False     

def empty(row):
    for cell in row:
        if len(cell)>0:
            return False
    return True

def unnamed(row):
    cell = row[0]
    if (cell.find('Unnamed') > -1  or cell.find('UnNamed') > -1 or cell.find('unnamed') > -1) :
        return True
    return False

def print_err(*a):
    print(*a, file=sys.stderr)

# make sure no two experiments are identical
def validateUniqueness(exprmntList):
    msgs = []
    for idx in range(0, len(exprmntList)-1):
        for jdx in range(idx+1, len(exprmntList)):
            if exprmntList[idx].equals(exprmntList[jdx]):
                msg = 'Duplicated experiment {}'.format(exprmntList[idx].name)
                msgs.append(msg)
    if len(msgs) > 0:
        return False, '\n'.join(msgs)
    return True, ""
        

def directoryAccessible(path):
    """
    Checks if a directory is accessible.
    
    Args:
        path: The path to the directory.
    
    Returns:
        True if the directory is accessible, False otherwise.
    """ 
    try:    
        os.access(path, os.R_OK)
    except OSError:
        return False
    else:   
        return True

def main():
    global variableName
    parser = argparse.ArgumentParser()
    parser.add_argument(u'-name', metavar = u'name of system', dest=u'name', required=True)
    parser.add_argument(u'-validate', action='store_true', required=False)
    parser.add_argument(u'-csvDir', metavar = u'directory where csv file is found', dest=u'csvDir', required=True)
    parser.add_argument(u'-yamlDir', metavar = u'directory where results are stored', dest=u'yamlDir', required=True)
    parser.add_argument(u'-descDir', metavar = u'directory where auxilary descriptions are stored', 
            dest=u'descDir', required=True)

    # csv input file
    parser.add_argument(u'-csvIn', metavar = u'input csv file name', dest=u'csv_input', required=True)
    parser.add_argument(u'-experiments', metavar = u'output file with list of experiment descriptions ', 
            dest=u'experiments', required=True)

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

    csvDir = args.csvDir
    yamlDir = args.yamlDir
    descDir = args.descDir

    # make sure we have access to these directories
    test_dirs = (csvDir, yamlDir, descDir)

    errs = []
    for tdir in test_dirs:
        if not os.path.isdir(tdir):
            errs.append('directory {} does not exist'.format(tdir))
        elif not directoryAccessible(tdir):
            errs.append('directory {} is not accessible'.format(tdir))

    if len(errs) > 0:
        for msg in errs:
            print(msg)
        exit(0)

    csv_input_file = os.path.join(csvDir, args.csv_input)
    experiment_output_file = os.path.join(yamlDir, args.experiments)
    symbol_desc_output_file = os.path.join(descDir, 'exprmnt.json')

    sysname = args.name

    if not os.path.isfile(csv_input_file):
        print("unable to open csv input file", csv_input_file)
        exit(0)

    experiments = []

    with open(csv_input_file, newline='') as rf:
        csvrdr = csv.reader(rf)
        for raw in csvrdr:
            row = []
            for v in raw:
                row.append(v.strip())

            if empty(row):
                continue

            if unnamed(row):
                continue

            row = cleanRow(row)
            if row[0].startswith('###') and row[0].find('END') > -1: 
                break

            if row[0] == 'Experiments':
                continue 

            variablesRow = (row[0].find('###') > -1) or (row[0].find('name') > -1)

            if variablesRow:
                for idx in range(1, len(row)):
                    if len(row[idx]) > 0:
                        variableName.append("".join(row[idx].split()))
                    else:
                        break

                maxCols = len(variableName)+1

                continue

            if comment(row[0]):
                continue
  
            if maxCols > 0:
                row = row[:maxCols]            

            experiments.append(ExperimentEntry(row))
            continue

        msgs = []
        for exprmnt in experiments:
            valid, msg = exprmnt.validate()
            if not valid:
                msgs.append(msg)
       
        if len(msgs) > 0:
            for msg in msgs:
                print(msg)
            exit(0)

        valid, msgs = validateUniqueness(experiments)
        if not valid:
            msgList = msgs.split('\n')
            for msg in msgList:
                print(msg)
            exit(0) 

        expList = []
        for exprmnt in experiments:
            expList.append(exprmnt.repDict())

    # make a description file of a dictionary indexed by sheet name,
    # with value of dictionary being a dictionary whose keys are the symbols,
    # with a list of values those symbols are assigned
    sheetDict = {}
    for exprmnt in experiments:
        for symbolKey, value in exprmnt.variableDict.items():
            keylist = symbolKey.split(',')
            if len(keylist) > 1:
                symbol = keylist[0]
                sheets = keylist[1:]
            else:
                symbol = symbolKey
                sheets = sheetNames

            for sheet in sheets:
                if not sheet in sheetDict:
                    sheetDict[sheet] = {}
                if symbol not in sheetDict[sheet]:
                    sheetDict[sheet][symbol] = []

                sheetDict[sheet][symbol].append(value)
            
    with open(symbol_desc_output_file, 'w') as wf:
        json.dump(sheetDict, wf) 
 
    with open(experiment_output_file, 'w') as wf:
        yaml.dump(expList, wf, default_flow_style=False)

def cleanRow(row):
    rtn = []
    for r in row:
        if r.startswith('#!'):
            r = ''                     
        elif len(rtn) > 0 and r.startswith('#'):
            break
        rtn.append(r)

    return rtn

if __name__ == "__main__":
	main()

