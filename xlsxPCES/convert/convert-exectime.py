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

validateFlag = False

operationIdx = 1
modelIdx = 0
pcktLenIdx = 2
execTimeIdx = 3

funcmodelIdx = 0
funcoperationIdx = 1
funcpcktLenIdx = 2
funcexecTimeIdx = 3

bndwdthIdx = 4

execTimeList = []
devOpTimeList = []
functionList = []

def varFloatScale(v,s):
    v = v.replace(' ','')
    here = v.find(')')
    return v[:here]+s+v[here:]  


class ExecTimeEntry:
    def __init__(self, ptype, row):
        self.ptype = ptype                      # cpu or accelerator
        self.model = row[modelIdx]
        self.op = row[operationIdx]
        self.pcktLen = row[pcktLenIdx]
        self.execTime = row[execTimeIdx]
    
    def validate(self):
        if not validateFlag:
            return True, ""

        msgs = []
        if not self.pcktLen.isdigit() or int(self.pcktLen) < 0:
            msg = 'execTime table packet length {} required to be positive integer'.format(self.pcktLen)
            msgs.append(msg)

        if len(self.model) == 0 and len(self.op) > 0:
            msg = 'expected operation {} to be assigned to non-empty processor name'.format(self.op)
            msgs.append(msg)
        elif len(self.model) == 0 and len(self.op) == 0:
            msg = 'expected operation and processor on exec timing line with pcktLen {} and execution time {}'.format(self.pcktLen, self.execTime)
            msgs.append(msg)

        try:
            tstflt = float(self.execTime)
            if tstflt < 0.0:
                msg = 'execTime processing {} required to be positive real'.format(self.execTime)
                msgs.append(msg)
        except:
            msg = 'execTime processing {} required to be positive real'.format(self.execTime)
            msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)
        return True, "" 

    def repDict(self):
        rd = {'identifier': self.op, 'cpumodel': self.model, 'pcktlen': self.pcktLen, 'exectime': self.execTime, 'param':""}
        if self.pcktLen.find('($') == -1:
            rd['pcktlen'] = int(self.pcktLen)

        if self.execTime.find(')') == -1:
            rd['exectime'] = float(self.execTime)/1e6
        else:
            rd['exectime'] = varFloatScale(self.execTime,'/1e6')       

        return rd

devOps = ('route','switch')

class DevOpTimeEntry:
    def __init__(self, devtype, row):
        self.devtype = devtype                      # model 
        self.model = row[modelIdx]
        self.devop = row[operationIdx]
        self.op = self.devop
        self.pcktLen = row[pcktLenIdx]
        self.execTime = row[execTimeIdx]
        self.bndwdth  = row[bndwdthIdx]

    def validate(self):
        if not validateFlag:
            return True, ""

        msgs = []
        if not self.pcktLen.isdigit() or int(self.pcktLen) < 0:
            msg = 'devOpTime table packet length {} required to be positive integer'.format(self.pcktLen)
            msgs.append(msg)

        if len(self.model) == 0 and len(self.devop) > 0:
            msg = 'expected operation {} to be assigned to non-empty device name'.format(self.devop)
            msgs.append(msg)
        elif len(self.model) == 0 and len(self.devop) == 0:
            msg = 'expected operation and processor on device op time line with pcktLen {} and execution time {}'.format(self.pcktLen, self.execTime)
            msgs.append(msg)

        try:
            tstflt = float(self.execTime)
            if tstflt < 0.0:
                msg = 'devOpTime processing {} required to be positive real'.format(self.execTime)
                msgs.append(msg)
        except:
            msg = 'devOpTime processing {} required to be positive real'.format(self.execTime)
            msgs.append(msg)

        try:
            tstflt = float(self.bndwdth)
            if tstflt < 0.0:
                pdb.set_trace()
                msg = 'devOpTime bandwidth {} required to be positive real'.format(self.bndwdth)
                msgs.append(msg)
        except:
            pdb.set_trace()
            msg = 'devOpTime bandwidth {} required to be positive real'.format(self.bndwdth)
            msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)
        return True, "" 

    def repDict(self):
        rd = {'devop': self.devop, 'model': self.model, 'pcktlen': int(self.pcktLen), 
            'bndwdth': self.bndwdth, 'param':"", 'devfunc':""}

        if self.execTime.find(')') == -1:
            rd['exectime'] = float(self.execTime)/1e6
        else:
            rd['exectime'] = varFloatScale(self.execTime, '/1e6')

        if self.bndwdth.find(')') == -1:
            rd['bndwdth'] = float(self.bndwdth)

        return rd

class FunctionEntry:
    def __init__(self, devtype, row):
        self.devtype = devtype                      # model 
        self.model = row[funcmodelIdx]
        self.devfunc  = row[funcoperationIdx]
        self.op = self.devfunc
        self.pcktLen = row[funcpcktLenIdx]
        self.execTime = row[funcexecTimeIdx]
        self.bndwdth  = 0.0

    def validate(self):
        if not validateFlag:
            return True, ""

        msgs = []
        if not self.pcktLen.isdigit() or int(self.pcktLen) < 0:
            msg = 'devOpTime table packet length {} required to be positive integer'.format(self.pcktLen)
            msgs.append(msg)

        if len(self.model) == 0 and len(self.devfunc) > 0:
            msg = 'expected device function {} to be assigned to non-empty device name'.format(self.devfunc)
            msgs.append(msg)
        elif len(self.model) == 0 and len(self.devfunc) == 0:
            msg = 'expected operation and processor on device op time line with pcktLen {} and execution time {}'.format(self.pcktLen, self.execTime)
            msgs.append(msg)

        try:
            tstflt = float(self.execTime)
            if tstflt < 0.0:
                msg = 'devOpTime processing {} required to be positive real'.format(self.execTime)
                msgs.append(msg)
        except:
            msg = 'devOpTime processing {} required to be positive real'.format(self.execTime)
            msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)
        return True, "" 

    def repDict(self):
        rd = {'devfunc': self.devfunc, 'model': self.model, 'pcktlen': int(self.pcktLen), 
            'bndwdth': 0.0, 'param':"", 'devop':""} 

        if self.execTime.find(')') == -1:
            rd['exectime'] = float(self.execTime)/1e6
        else:
            rd['exectime'] = varFloatScale(self.execTime, '/1e6')

        return rd

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

def cleanRow(row):
    rtn = []
    for r in row:
        if r.startswith('#!'):
            r = ''                     
        elif len(rtn) > 0 and r.startswith('#'):
            break
        rtn.append(r)

    return rtn


def print_err(*a):
    print(*a, file=sys.stderr)

def validateUniqueness():
    if not validateFlag:
        return True, ""

    msgs = []
    seen = {}
    for entry in devOpTimeList:
       if entry.devop in seen:
            msg = 'expect dev time op table entry {} to be unique'.format(entry.devop)
            msgs.append(msg)

    seen = {}
    for entry in execTimeList:
       if (entry.model, entry.op) in seen:
            msg = 'expect exec time table entry ({},{}) to be unique'.format(entry.model, entry.op)
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
    global validateFlag

    parser = argparse.ArgumentParser()
    parser.add_argument(u'-name', metavar = u'name of system', dest=u'name', required=True)
    parser.add_argument(u'-validate', action='store_true', required=False)

    parser.add_argument(u'-csvDir', metavar = u'directory where csv file is found', dest=u'csvDir', required=True)
    parser.add_argument(u'-yamlDir', metavar = u'directory where results are stored', dest=u'yamlDir', required=True)
    parser.add_argument(u'-descDir', metavar = u'directory where auxilary descriptions are stored', 
            dest=u'descDir', required=True)

    # csv input file
    parser.add_argument(u'-csvIn', metavar = u'input csv file name', dest=u'csv_input', required=True)

    parser.add_argument(u'-cpuOpsDescOut', metavar = u'output input file with dictionary of ops given @cpu model', dest=u'cpuOpsDesc_output', required=True)

    parser.add_argument(u'-modelDescOut', metavar = u'output file with dictionary of models associated with a type of device', 
                            dest=u'modelDesc_output', required=True)

    # output in the format of cp.yaml
    parser.add_argument(u'-funcExecOut', metavar = u'output funcExec name', dest=u'funcExec_output', required=True)

    # output in the format of cp.yaml
    parser.add_argument(u'-devExecOut', metavar = u'output devExec name', dest=u'devExec_output', required=True)

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

    if args.validate is False:
        validateFlag = False
    else:
        validateFlag = True


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
        exit(1)

    csv_input_file = os.path.join(csvDir, args.csv_input)
    func_exec_output_file = os.path.join(yamlDir, args.funcExec_output)

    dev_exec_output_file = os.path.join(yamlDir, args.devExec_output)

    dev_exec_desc_output_file = os.path.join(descDir, args.devExec_output)
    dev_exec_desc_output_file = dev_exec_desc_output_file.replace('.yaml','.json')
    
    cpu_ops_output_file = os.path.join(descDir, args.cpuOpsDesc_output)
    dev_model_output_file = os.path.join(descDir, args.modelDesc_output)

    sysname = args.name

    if not os.path.isfile(csv_input_file):
        print("unable to open csv input file", csv_input_file)
        exit(0)

    msgs = []
    with open(csv_input_file, newline='') as rf:
        csvrdr = csv.reader(rf)
        for raw in csvrdr:
            row = []
            for v in raw:
                #row.append(''.join(v.split()))
                row.append(v.strip())

            if comment(row[0]):
                continue

            if empty(row):
                continue

            if unnamed(row):
                continue

            row = cleanRow(row)

            if row[0].find("CPU") > -1 and row[0].find('Entries') > 0:
                cpuEntries = True
                maxCols = 4
                accelEntries = False
                routerEntries = False
                switchEntries = False
                functionEntries = False
                continue
               
            if row[0].find("Accel") > -1 and row[0].find('Entries') > 0:
                cpuEntries = False
                accelEntries = True
                maxCols = 4
                routerEntries = False
                switchEntries = False
                functionEntries = False
                continue
               
            if row[0].find("Router") > -1 and row[0].find('Entries') > 0:
                cpuEntries = False
                accelEntries = False
                routerEntries = True
                maxCols = 5
                switchEntries = False
                functionEntries = False
                continue
               
            if row[0].find("Switch") > -1 and row[0].find('Entries') > 0:
                cpuEntries = False
                accelEntries = False
                routerEntries = False
                switchEntries = True
                functionEntries = False
                maxCols = 5
                continue

            if row[0].find("Function") > -1: 
                cpuEntries = False
                accelEntries = False
                routerEntries = False
                switchEntries = False
                functionEntries = True
                maxCols = 4
                continue

            row = row[:maxCols]

            if cpuEntries: 
                execTimeList.append(ExecTimeEntry('CPU', row))
                continue

            if accelEntries: 
                execTimeList.append(ExecTimeEntry('Accelerator', row))
                continue

            if routerEntries:
                devOpTimeList.append(DevOpTimeEntry('Router', row))
                continue

            if switchEntries:
                devOpTimeList.append(DevOpTimeEntry('Switch', row))
                continue

            if functionEntries:
                functionList.append(FunctionEntry('Function', row))
                continue

    for entry in execTimeList:
        valid, msg = entry.validate()
        if not valid:
            msgs.append(msg)

    for entry in devOpTimeList:
        valid, msg = entry.validate()
        if not valid:
            msgs.append(msg)

    for entry in functionList:
        valid, msg = entry.validate()
        if not valid:
            msgs.append(msg)

    valid, msg = validateUniqueness()
    if not valid:
        msgs.append(msg)

    if len(msgs) > 0:
        for msgrp in msgs:
            msgrp = msgrp.split('\n')
            for msg in msgrp:
                print(msg)

        exit(1)

    timesByOp = {}
    cpuOps = {}
    modelDict = {'CPU': {}, 'Accelerator': {}, 'Switch': {}, 'Router': {}}

    for entry in execTimeList:
        cpuOpsKey = entry.ptype+"%"+entry.model
        if cpuOpsKey not in cpuOps:
            cpuOps[cpuOpsKey] = []

        if entry.op not in timesByOp:
            timesByOp[entry.op] = []

        timesByOp[entry.op].append( entry.repDict() )

        if entry.op not in cpuOps[cpuOpsKey]:
            cpuOps[cpuOpsKey].append( entry.op )

        try:
            if entry.model not in modelDict[entry.ptype]:
                modelDict[entry.ptype][entry.model] = [] 
        except:
            print("oops")
            exit(1)

        if entry.op not in modelDict[entry.ptype][entry.model]:
            modelDict[entry.ptype][entry.model].append(entry.op)

    tableDict = {'listname' : sysname, 'times': timesByOp }
    with open(func_exec_output_file, 'w') as wf:
        yaml.dump(tableDict, wf, default_flow_style=False)

    with open(cpu_ops_output_file, 'w') as wf:
        json.dump(cpuOps, wf)

    opsByModel = {}
    timesByOp  = {}

    devOpList = devOpTimeList
    devOpList.extend(functionList)

    for entry in devOpTimeList:
        if entry.model not in opsByModel:
            opsByModel[entry.model] = []

        if entry.op not in timesByOp:
            timesByOp[entry.op] = []

        timesByOp[entry.op].append( entry.repDict() )

        if entry.devtype != 'Function' and entry.model not in modelDict[entry.devtype]:
            modelDict[entry.devtype][entry.model] = [] 

        if entry.devtype != 'Function' and entry.op not in modelDict[entry.devtype][entry.model]:      
            modelDict[entry.devtype][entry.model].append(entry.op) 

    tableDict = {'listname': sysname, 'times': timesByOp }
    with open(dev_exec_output_file, 'w') as wf:
        yaml.dump(tableDict, wf, default_flow_style=False)
        
    with open(dev_exec_desc_output_file, 'w') as wf:
        json.dump(tableDict, wf)
        
    with open(dev_model_output_file, 'w') as wf:
        json.dump(modelDict, wf)


if __name__ == "__main__":
	main()

