import csv
import pdb
import yaml
import json
import sys
import os
import argparse


# Globals
cpusDict = {}
mappingList = []
cpFunc = []
cpuDescList = []
cpuObs = []
endpts2models = {}
cmpptnFuncPairs = {}
cpuOps = {}

cmpptnNames = []

funcDescDict = {}

cpuNameIdx = 0
cpuModelIdx = 1
cpuCoresIdx = 2
cpuAccelNameIdx = 3
cpuAccelModelIdx = 4

mappingCmpPtnIdx = 1
mappingFuncIdx = 2
mappingEndptIdx = 3
mappingPriIdx = 4

endpoints = False
mapping = False

def print_err(*a) : 
    print(*a, file=sys.stderr)

class Mapping():
    def __init__(self, row):
        self.cmpptn = row[0]
        self.label  = row[1]
        self.cpu = row[2]
        self.pri = row[3]

        cpFunc.append((self.cmpptn, self.label))
  
    def validate(self):
        msgs = []

        if self.cmpptn not in cmpptnNames:
            msg = 'mapping cites comp pattern name "{}" not found in system model'.format(self.cmpptn)
            msgs.append(msg)
        else:
            valid, cmsg = validateFuncInCP(self.cmpptn, self.label)
            if not valid:
                msg = 'mapping expect function {} to be associated with cmpptn {}'.format(self.label, self.cmpptn)
                msgs.append(msg)

        bypass = False
        present = (self.cpu in endpts2models)
        if not present:
            msg = 'expected endpoint device {} to be expressed in topology description'.format(self.cpu)
            msgs.append(msg)
            bypass = True
        else:
            model = endpts2models[self.cpu]

        if not bypass: 
            key = 'CPU%'+model
            # get list of op codes from exec table associated with this model

            # continue only if there are some to check against
            if key not in cpuOps:
                bypass = True 
            else:
                opsFromExec = cpuOps[key]
 
        if not bypass:
            # the device model is in variable 'model'. Get the list
            # of op codes for this function as exported by the topo portion
            selfKey = (self.cmpptn, self.label) 
            
            if (selfKey in cmpptnFuncPairs):
                opsFromTopo = cmpptnFuncPairs[selfKey]
                
                # check each of these against the ops from Exec to see if present
                for op in opsFromTopo: 
                    if not op in opsFromExec: 
                        msg = 'expected operation {} for ({},{}) to be func exec table associated with model to which endpoint {} is attached'.format(op, self.cmpptn, self.label, self.cpu)
                        msgs.append(msg)
                    

        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

def validateFuncInCP(cmpptn, label):
    if len(funcDescDict)==0:
        return True

    msgs = []
    if cmpptn not in funcDescDict:
        msg = 'expected cmp ptn {} to be in function description dictionary'.format(cmpptn)
        msgs.append(msg)

    elif label not in funcDescDict[cmpptn]:
        msg = 'expected func {} to be part of cmp ptn {}'.format(label, cmpptn)
        msgs.append(msg)

    if len(msgs) > 0:
        return False, '\n'.join(msgs)
    
    return True, ""
 
def empty(row):
    for cell in row:
        if len(cell)>0:
            return False
    return True

def unnamed(row):
    for cell in row:
        if cell.find('Unnamed') > -1  or cell.find('UnNamed') > -1 or cell.find('unnamed') > -1 :
            return True

    return False

# validate that mappings are unique
def validateUniqueness():
    msgs = []
    seen = {}
    for idx in range(0,len(cpFunc)):
        for jdx in range(idx+1, len(cpFunc)):
            if cpFunc[idx] == cpFunc[jdx]:
                msg = 'duplicated mapping of ({},{})'.format(cpFunc[idx][0], cpFunc[idx][1])
                msgs.append(msg)

    if len(msgs) > 0:
        return False, '\n'.join(msgs)

    return True, ""

def validateCoverage():
    msgs = []
    covered = {}
    for mapping in mappingList:
        covered[(mapping.cmpptn, mapping.label)] = True

    for cmpptn, funcList in funcDescDict.items():
        for func in funcList:
            if (cmpptn, func) not in covered:
                msg = 'expected ({},{}) to have mapping'.format(cmpptn, func)
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
    global cpuDescList, funcDescDict, endpts2models, cmpptnFuncPairs, cpuOps, cmpptnNames

    parser = argparse.ArgumentParser()
    parser.add_argument(u'-name', metavar = u'name of system', dest=u'name', required=True)

    parser.add_argument(u'-csvDir', metavar = u'directory where csv file is found', dest=u'csvDir', required=True)
    parser.add_argument(u'-resultsDir', metavar = u'directory where results are stored', dest=u'resultsDir', required=True)
    parser.add_argument(u'-descDir', metavar = u'directory where auxilary descriptions are stored', 
            dest=u'descDir', required=True)

    # csv input file
    parser.add_argument(u'-csvIn', metavar = u'input csv file name', dest=u'csv_input', required=True)

    # input file in dict format used by convert-cp
    # whose keys are the comp pattern names, and the value of each
    # is a list of function labels bound to that comp pattern
    parser.add_argument(u'-funcsDescIn', metavar = u'input file with description of comp pattern functions', dest=u'funcsDesc_input', required=True)

    # input file of list of cpu descriptions as created by convert-topo, each member a dictionary 
    # with cpu (endpoint) 'name', 'model', 'cores', and dictionary of accelerators
    parser.add_argument(u'-cpuDescIn', metavar = u'input file of cpu Desc types', dest=u'cpuDesc_input', required=True)

    # cpuOps[{CPU, Switch, Accel, Router}+"-"+model] -> [ops for that type of device]
    parser.add_argument(u'-cpuOpsDescIn', metavar = u'input file of cpu Desc types', dest=u'cpuOpsDesc_input', required=True)

    # input file of list of (cmpptn, func, timingcode)
    parser.add_argument(u'-tcDesc', metavar = u'input file of timing code information', dest=u'tcDesc_input', required=True)

    # output file of mapping table
    parser.add_argument(u'-map', metavar = u'output file of mapping output', dest=u'map_output', required=True)

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
    resultsDir = args.resultsDir
    descDir = args.descDir

    # make sure we have access to these directories
    test_dirs = (csvDir, resultsDir, descDir)

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

    topoName             = args.name
    csv_input_file       = os.path.join(csvDir, args.csv_input)
    funcsDesc_input_file     = os.path.join(descDir, args.funcsDesc_input)
    cpuDesc_input_file       = os.path.join(descDir, args.cpuDesc_input)
    cpuOpsDesc_input_file    = os.path.join(descDir, args.cpuOpsDesc_input)
    tcDesc_input_file        = os.path.join(descDir, args.tcDesc_input)
    map_output_file          = os.path.join(resultsDir, args.map_output)

    input_files = (csv_input_file, funcsDesc_input_file, cpuDesc_input_file, tcDesc_input_file)

    errs = 0
    for file_name in input_files:
        if not os.path.isfile(file_name):
            print_err('unable to open {} input file'.format(file_name))
            errs += 1 

    if errs>0:
        exit(1)
 
    if funcsDesc_input_file is not None:
        with open(funcsDesc_input_file,'r') as rf:
            funcDescDict = json.load(rf)
            cmpptnNames = funcDescDict.keys()

    endpts2models = {}
    if cpuDesc_input_file is not None:
        with open(cpuDesc_input_file,'r') as rf:
            cpuDescList = json.load(rf)

            # build a list mapping endpoints to models
            for cpuDesc in cpuDescList:
                endpts2models[cpuDesc['name']] = cpuDesc['model']

    if cpuOpsDesc_input_file is not None:
        with open(cpuOpsDesc_input_file,'r') as rf:
            cpuOps = json.load(rf)

    if tcDesc_input_file is not None:
        with open(tcDesc_input_file,'r') as rf:
            tcList = json.load(rf)
            for tc in tcList:
                fcList = []
                for _, fc in tc['timingcode'].items():
                    fcList.append(fc)
                cmpptnFuncPairs[(tc['cmpptn'], tc['label'])] = fcList

    msgs = []
    with open(csv_input_file, newline='') as rf:
        csvrdr = csv.reader(rf)
        for raw in csvrdr:
            row = []
            for v in raw:
                row.append(v.strip())

            if row[0].find('#') > -1:
                continue

            if empty(row):
                continue

            if unnamed(row):
                continue

            matchCode = "None"
            rowTypes = ["Mapping"]
            for rowtype in rowTypes:
                if row[0].find(rowtype) > -1:
                    matchCode = rowtype 
                    break

            match matchCode:
                case "Mapping":
                    mapping = True
                    continue

            if mapping:
                mappingList.append(Mapping(row))
                continue

    # validate that the mappings declared are unique
    valid, msg = validateUniqueness()
    if not valid:
        msgs.append(msg)

    # ensure that every function has a mapping
    valid, msg = validateCoverage()
    if not valid:
        msgs.append(msg)

    # validate individual mappings
    for mapping in mappingList:
        valid, msg = mapping.validate()
        if not valid:
            msgs.append(msg)

    if len(msgs) > 0 :
        for msgrp in msgs:
            msgrp = msgrp.split('\n')
            for msg in msgrp:
                print_err(msg)

        exit(1)

    if len(msgs) > 0:
        for msgrp in msgs:
            msgrp = msgrp.split('\n')
            for msg in msgrp: 
                print_err(msg)
        exit(1)

    # create the output. gather the functions for each comp pattern and make the mapping entry
    cmpptnMap = {}
    for mapDesc in mappingList:
        if mapDesc.cmpptn not in cmpptnMap:
            cmpptnMap[mapDesc.cmpptn] = {} 
        cmpptnMap[mapDesc.cmpptn][mapDesc.label] = mapDesc.cpu+','+str(mapDesc.pri)

    mapDict = {'dictname': topoName, 'map': {}}    

    for cmpptn, funcMap in cmpptnMap.items():
        mapDict['map'][cmpptn] = {'patternname': cmpptn, 'funcmap': funcMap} 

    with open(map_output_file, 'w') as wf:
        yaml.dump(mapDict, wf)

if __name__ == '__main__':
    main()
