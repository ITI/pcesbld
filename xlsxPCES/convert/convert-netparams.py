import csv
import pdb
import yaml
import json
import sys
import os
import argparse


# Globals
networkList = []
switchList  = []
routerList  = []
endptList   = []
intrfcList  = []
flowList    = []

validateFlag = False

netAttrbIdx = {}
netParamIdx = {}
netAttrb = ('name', 'groups', 'media', 'scale', '*')
netParam  = ('latency', 'bandwidth', 'capacity', 'trace')
netParamLater = ('bacgrndBW', 'drop')


switchAttrbIdx = {}
switchParamIdx = {}
switchAttrb = ('name', 'groups', 'model', '*')
switchParam  = ('model', 'trace', 'func')
switchParamLater = ('buffer', 'simple', 'drop')

routerAttrbIdx = {}
routerParamIdx = {}
routerAttrb = ('name', 'groups', 'model', '*')
routerParam  = ('model', 'trace','func')
routerParamLater = ('buffer', 'simple', 'drop')

endptAttrbIdx = {}
endptParamIdx = {}
endptAttrb = ('name', 'groups', 'model', '*')
endptParam = ('model', 'interruptdelay', 'trace')
endptParamLater = ('bckgrndrate', 'bckgrndsrv')

intrfcAttrbIdx = {}
intrfcParamIdx = {}
intrfcAttrb = ('name', 'groups', 'devtype', 'devname', 'media', 'faces', '*')
intrfcParam = ('latency', 'bandwidth', 'mtu', 'trace','detailedflow')
intrfcParamLater = ('rsrvd','drop')

flowAttrbIdx = {}
flowParamIdx = {}
flowAttrb = ('name', 'groups', 'srcdev', 'dstdev', '*')
flowParam = ('reqrate', 'classid', 'elastic')

attrbDesc = {}

devOpDict = {}
devFuncDict = {}

def createIdx():
    for idx in range(0,len(netAttrb)):
        netAttrbIdx[ netAttrb[idx] ] = idx
    for idx in range(0, len(netParam)):
        netParamIdx[ idx ] = len(netAttrb)+idx

    for idx in range(0,len(switchAttrb)):
        switchAttrbIdx[ switchAttrb[idx] ] = idx
    for idx in range(0, len(switchParam)):
        switchParamIdx[ idx ] = len(switchAttrb)+idx

    for idx in range(0,len(routerAttrb)):
        routerAttrbIdx[ routerAttrb[idx] ] = idx
    for idx in range(0, len(routerParam)):
        routerParamIdx[ idx ] = len(routerAttrb)+idx

    for idx in range(0,len(endptAttrb)):
        endptAttrbIdx[ endptAttrb[idx] ] = idx
    for idx in range(0, len(endptParam)):
        endptParamIdx[ idx ] = len(endptAttrb)+idx

    for idx in range(0,len(intrfcAttrb)):
        intrfcAttrbIdx[ intrfcAttrb[idx] ] = idx

    for idx in range(0, len(intrfcParam)):
        intrfcParamIdx[ idx ] = len(intrfcAttrb)+idx

    for idx in range(0,len(flowAttrb)):
        flowAttrbIdx[ flowAttrb[idx] ] = idx
    for idx in range(0, len(flowParam)):
        flowParamIdx[ idx ] = len(flowAttrb)+idx

network = False
switch = False
router  = False
endpoint = False
interface = False

def repAttrb(attrbDict):
    ra = []
    for key, value in attrbDict.items():
        if len(value) == 0:
            continue
        if key=='*':
            ra.append(1)
            continue

        ra.append(value)
    return ra

def repParam(obj, attrbs, param, value):
    rp = {'paramObj': str(obj), 'attributes': [], 'param': str(param), 'value': value}
    for attrb in attrbs:
        rp['attributes'].append(attrb)
    return rp

class Network:
    def __init__(self, row): 
        self.attrb = {}
        self.param = {}
        self.groups = []

        for idx in range(0, len(netAttrb)):
            self.attrb[netAttrb[idx]] = row[idx]

        if len(self.attrb['*']):
            self.attrb['*'] = cnvrtBool(self.attrb['*'])
            if self.attrb['*'] == 0:
                self.attrb['*'] = ''

        if len(self.attrb['groups']) > 0:
            self.groups = self.attrb['groups'].split(',')

        numAttrb = len(netAttrb)
        for idx in range(0, len(netParam)):
            self.param[netParam[idx]] = row[numAttrb+idx]

    def repDict(self):
        rdList = []
        for idx in range(0, len(netParam)):
            paramName = netParam[idx]
            paramValue = self.param[paramName]
            numericValue = isNumeric(paramValue)
 
            if len(str(paramValue)) > 0:
                #netParam  = ('latency', 'bandwidth', 'capacity', 'trace')
                if numericValue:
                    if paramName in ('latency'):
                        paramValue = float(paramValue)/1e6
                    if paramName in ('bandwidth', 'capacity'):
                        paramValue = float(paramValue) 

                if paramName == 'trace' and len(str(paramValue))>0:
                    paramValue = cnvrtBool(paramValue)

                rd = {'paramObj': 'Network', 'attributes': [], 'param': paramName, 'value': paramValue}
                for jdx in range(0, len(netAttrb)):
                    attrbName = netAttrb[jdx]
                    attrbValue = self.attrb[attrbName]
                    if len(attrbValue) > 0:
                        attrbDict = {'attrbname': attrbName, 'attrbvalue' : attrbValue}
                        rd['attributes'].append(attrbDict)
                
                rdList.append(rd)              

        return rdList

    def validate(self):
        # netAttrb = ('name', 'group', 'media', 'scale', '*')
        # netParm  = ('latency', 'bandwidth', 'capacity', 'trace')
        errs = []
        warnings = []

        media = self.attrb['media']
        scale = self.attrb['scale']
        wildcard = self.attrb['*']

        trace = self.param['trace']
        valid, msg = validateBool(trace)
        if not valid:
            msg = 'error: Network param lists non-Boolean representation '"{}"' for trace parameter'.format(trace)
            errs.append(msg)
        else:
            self.param['trace'] = cnvrtBool(trace)

        if not validateFlag:
            return True, ""
 
        # warn if 
        #  - the network entry lists a network name not found in the attributes list
        #  - the network entry lists a group not found in the attributes list
        # generate an error if
        #  - scale is not legal (LAN, WAN, T3, T2, T1)
        #  - media is not legal (wired, wireless)
        #
        if len(scale) > 0 and scale not in ('LAN', 'WAN', 'T3', 'T2', 'T1'):
            msg = 'error: Network attribute list give unrecognized scale type "{}"'.format(scale)
            errs.append(msg)

        if len(media) > 0 and media not in ('wired', 'wireless'):
            msg = 'error: Network attribute list give unrecognized media type "{}"'.format(media)
            errs.append(msg)

        if (isinstance(wildcard, str) and len(wildcard) > 0) or isinstance(wildcard, int):
            valid, msg = validateBool(wildcard)
            if not valid:
                msg = 'error: Network attribute gives non-Boolean wildcard description "{}"'.format(wildcard)
                errs.append(msg)
            else:
                wcValue = cnvrtBool(wildcard)

                # if the wildcard is not true, clear it
                if wcValue == 0:
                    self.attrb['*'] = ''

        attrbList = attrbDesc['Network']
        netName = self.attrb['name']

        if len(netName) > 0:
            nameFound = False
            for attrb in attrbList:
                if attrb['name'] == netName:
                    nameFound = True
                    break
            if not nameFound:
                msg = 'warning: Network attribute list gives network name "{}" not found in the system model'.format(netName)
                warnings.append(msg)

        if len(self.groups) > 0:
            groupsFound = {}
            for attrb in attrbList:
                if len(attrb['groups']) > 0:
                    for grp in attrb['groups']:
                        groupsFound[grp] = True

            # see if any group in self.group was not observed
            for grp in self.groups:
                if not grp in groupsFound:
                    msg = 'warning: Network attribute list gives group name "{}" not found in the system model'.format(grp)
                    warnings.append(msg)


        testParams = ('latency', 'bandwidth', 'capacity')
        for param in testParams:
            value = self.param[param]
            if len(value) == 0:
                continue

            # revisit for better sanity check with experiment variables
            if value.find('$') > -1:
                continue

            try:
                floatvalue = float(value)
                if floatvalue < 0.0:
                    msg = 'error: Network param lists negative "{}"'.format(param)
                    errs.append(msg)
            except:
                msg = 'error: Network param lists non-floating point "{}"'.format(param)
                errs.append(msg)

        if len(warnings) > 0:
            for msg in warnings:
                print_err(msg)
          
        if len(errs) > 0:
            return False, '\n'.join(errs)

        return True, ""

class Switch:
    def __init__(self, row): 
        self.attrb = {}
        self.param = {}
        self.groups = []
 
        for idx in range(0, len(switchAttrb)):
            self.attrb[switchAttrb[idx]] = row[idx]

        if len(self.attrb['*']) > 0:
            self.attrb['*'] = cnvrtBool(self.attrb['*'])
            if self.attrb['*'] == 0:
                self.attrb['*'] = '' 
  
        if len(self.attrb['groups']) > 0:
            self.groups = self.attrb['groups'].split(',')

        numAttrb = len(switchAttrb)
        for idx in range(0, len(switchParam)):
            self.param[switchParam[idx]] = row[numAttrb+idx]

    def repDict(self):
        rdList = []
        for idx in range(0, len(switchParam)):
            paramName = switchParam[idx]
            paramValue = self.param[paramName]

            if len(str(paramValue)) > 0:
                rd = {'paramObj': 'Switch', 'attributes': [], 'param': paramName, 'value': paramValue}
                for jdx in range(0, len(switchAttrb)):
                    attrbName = switchAttrb[jdx]
                    attrbValue = self.attrb[attrbName]
                    if len(str(attrbValue)) > 0:
                        attrbDict = {'attrbname': attrbName, 'attrbvalue' : attrbValue}
                        rd['attributes'].append(attrbDict)
                
                rdList.append(rd)              

        return rdList

    def validate(self):
        # switchAttrb = ('name', 'group', 'model', '*')
        # switchParam  = ('model', 'trace', 'func')
 
        errs = []
        warnings = []

        trace = self.param['trace']
        valid, msg = validateBool(trace)
        if not valid:
            msg = 'error: Switch param lists non-Boolean representation '"{}"' for trace parameter'.format(trace)
            errs.append(msg)
        else:
            self.param['trace'] = cnvrtBool(trace)

        if not validateFlag:
            return True, "" 

        # warn if 
        #  - the switch entry lists a switch name not found in the attributes list
        #  - the switch entry lists a group not found in the attributes list
        #  - the switch entry lists a model not found in the attributes list
        # generate an error if
        #  - the switch entry lists a model parameter that is not found in the system model
        
        attrbList = attrbDesc['Switch']
        switchName = self.attrb['name']
        switchModel = self.attrb['model']
        wildcard = self.attrb['*']

        if (isinstance(wildcard, str) and len(wildcard) > 0) or isinstance(wildcard, int):
            valid, msg = validateBool(wildcard)
            if not valid:
                msg = 'error: Switch attribute gives non-Boolean wildcard description "{}"'.format(wildcard)
                errs.append(msg)
            else:
                wcValue = cnvrtBool(wildcard)

                # if the wildcard is not true, clear it
                if wcValue == 0:
                    self.attrb['*'] = ''

        if len(switchName) > 0:
            nameFound = False
            for attrb in attrbList:
                if attrb['name'] == switchName:
                    nameFound = True
                    break
            if not nameFound:
                msg = 'warning: Switch attribute list gives switch name "{}" not found in the system model'.format(switchName)
                warnings.append(msg)

        if len(switchModel) > 0:
            modelFound = False
            for attrb in attrbList:
                if attrb['model'] == switchModel:
                    modelFound = True
                    break
            if not modelFound:
                msg = 'warning: Switch attribute list gives switch model "{}" not found in the system model'.format(switchModel)
                warnings.append(msg)

        if len(self.groups) > 0:
            groupsFound = {}
            for attrb in attrbList:
                if len(attrb['groups']) > 0:
                    for grp in attrb['groups']:
                        groupsFound[grp] = True

            # see if any group in self.group was not observed
            for grp in self.groups:
                if not grp in groupsFound:
                    msg = 'warning: Switch attribute list gives group name "{}" not found in the system model'.format(grp)
                    warnings.append(msg)

        # check the legality of the switch parameters
        modelParam = self.param['model']
        if len(modelParam) > 0:
            modelFound = False
            for attrb in attrbList:
                if attrb['model'] == modelParam:
                    modelFound = True
                    break

            if not modelFound:
                msg = 'error: Switch parameter list gives switch model "{}" not found in the system model'.format(modelParam)
                errs.append(msg)

        func = self.param['func']
        if len(func) > 0:
            # split function across ','
            pieces = func.split(',')
            if len(pieces) != 2:
                msg = 'error: Switch function format is functionName,applicationCode'
                errs.append(msg)
            else:
                funcName = pieces[0].strip()
                funcApp  = pieces[1].strip()

                # ensure that identified function is '*' or was specified in exectimes file
                if funcName != '*' and funcName not in devFuncDict:
                    msg = 'error: Switch function {} needs to appear in device function execution times list'.format(funcName)
                    errs.append(msg)

                elif funcName != '*' and switchModel not in devFuncDict[funcName]:
                    msg = 'error: Switch function {} needs to appear in device function execution times list'.format(funcName)
                    errs.append(msg)
            
                elif funcApp not in ('cross', 'interior', '*'):
                    msg = 'error: Switch function application needs to be one of "{}"'.format('cross, interior, *')
                    errs.append(msg)

                self.param['func'] = funcName+','+funcApp
                
        if len(warnings) > 0:
            for msg in warnings:
                print_err(msg)
          
        if len(errs) > 0:
            return False, '\n'.join(errs)

        return True, ""

class Router:
    def __init__(self, row): 
        self.attrb = {}
        self.param = {}
        self.groups = []
 
        for idx in range(0, len(routerAttrb)):
            self.attrb[routerAttrb[idx]] = row[idx]

        if len(self.attrb['*']) > 0:
            self.attrb['*'] = cnvrtBool(self.attrb['*'])
            if self.attrb['*'] == 0:
                self.attrb['*'] = ''
 
        if len(self.attrb['groups']) > 0:
            self.groups = self.attrb['groups'].split(',')

        numAttrb = len(routerAttrb)
        for idx in range(0, len(routerParam)):
            self.param[routerParam[idx]] = row[numAttrb+idx]

    def repDict(self):
        rdList = []
        for idx in range(0, len(routerParam)):
            paramName = routerParam[idx]
            paramValue = self.param[paramName]

            if len(str(paramValue)) > 0:
                rd = {'paramObj': 'Router', 'attributes': [], 'param': paramName, 'value': paramValue}
                for jdx in range(0, len(routerAttrb)):
                    attrbName = routerAttrb[jdx]
                    attrbValue = self.attrb[attrbName]
                    if len(str(attrbValue)) > 0:
                        attrbDict = {'attrbname': attrbName, 'attrbvalue' : attrbValue}
                        rd['attributes'].append(attrbDict)
                
                rdList.append(rd)              

        return rdList

    def validate(self):
        # routerAttrb = ('name', 'group', 'model', '*')
        # routerParam  = ('model', 'trace')
 
        errs = []
        warnings = []

        trace = self.param['trace']
        valid, msg = validateBool(trace)
        if not valid:
            msg = 'error: Router param lists non-Boolean representation '"{}"' for trace parameter'.format(trace)
            errs.append(msg)
        else:
            self.param['trace'] = cnvrtBool(trace)

        if not validateFlag:
            return True, ""

        # warn if 
        #  - the router entry lists a router name not found in the attributes list
        #  - the router entry lists a group not found in the attributes list
        #  - the router entry lists a model not found in the attributes list
        # generate an error if
        #  - the router entry lists a model parameter that is not found in the system model
        
        attrbList = attrbDesc['Router']
        routerName = self.attrb['name']
        routerModel = self.attrb['model']

        wildcard = self.attrb['*']

        if (isinstance(wildcard, str) and len(wildcard) > 0) or isinstance(wildcard, int):
            valid, msg = validateBool(wildcard)
            if not valid:
                msg = 'error: Router attribute gives non-Boolean wildcard description "{}"'.format(wildcard)
                errs.append(msg)
            else:
                wcValue = cnvrtBool(wildcard)

                # if the wildcard is not true, clear it
                if wcValue == 0:
                    self.attrb['*'] = ''

        if len(routerName) > 0:
            nameFound = False
            for attrb in attrbList:
                if attrb['name'] == routerName:
                    nameFound = True
                    break
            if not nameFound:
                msg = 'warning: Router attribute list gives router name "{}" not found in the system model'.format(routerName)
                warnings.append(msg)

        if len(routerModel) > 0:
            modelFound = False
            for attrb in attrbList:
                if attrb['model'] == routerModel:
                    modelFound = True
                    break
            if not modelFound:
                msg = 'warning: Router attribute list gives router model "{}" not found in the system model'.format(routerModel)
                warnings.append(msg)

        if len(self.groups) > 0:
            groupsFound = {}
            for attrb in attrbList:
                if len(attrb['groups']) > 0:
                    for grp in attrb['groups']:
                        groupsFound[grp] = True

            # see if any group in self.group was not observed
            for grp in self.groups:
                if not grp in groupsFound:
                    msg = 'warning: Router attribute list gives group name "{}" not found in the system model'.format(grp)
                    warnings.append(msg)

        # check the legality of the router parameters
        modelParam = self.param['model']
        if len(modelParam) > 0:
            modelFound = False
            for attrb in attrbList:
                if attrb['model'] == modelParam:
                    modelFound = True
                    break

            if not modelFound:
                msg = 'error: Router parameter list gives router model "{}" not found in the system model'.format(modelParam)
                errs.append(msg)

        func = self.param['func']
        if len(func) > 0:
            # split function across ','
            pieces = func.split(',')
            if len(pieces) != 2:
                msg = 'error: Router function format is functionName,applicationCode'
                errs.append(msg)
            else:
                funcName = pieces[0].strip()
                funcApp  = pieces[1].strip()

                # ensure that identified function is '*' or was specified in exectimes file
                if funcName != '*' and funcName not in devFuncDict:
                    msg = 'error: Router function {} needs to appear in device function execution times list'.format(funcName)
                    errs.append(msg)

                elif funcName != '*' and routerModel not in devFuncDict[funcName]:
                    msg = 'error: Router function {} needs to appear in device function execution times list'.format(funcName)
                    errs.append(msg)
            
                elif funcApp not in ('cross', 'interior', '*'):
                    msg = 'error: Router function application needs to be one of "{}"'.format('cross, interior, *')
                    errs.append(msg)

                self.param['func'] = funcName+','+funcApp
                
        if len(warnings) > 0:
            for msg in warnings:
                print_err(msg)
          
        if len(errs) > 0:
            return False, '\n'.join(errs)

        return True, ""

class Endpoint:
    def __init__(self, row): 
        self.attrb = {}
        self.param = {}
        self.groups = []
 
        for idx in range(0, len(endptAttrb)):
            self.attrb[endptAttrb[idx]] = row[idx]

        if len(self.attrb['*']):
            self.attrb['*'] = cnvrtBool(self.attrb['*'])
            if self.attrb['*'] == 0:
                self.attrb['*'] = ''
 
        if len(self.attrb['groups']) > 0:
            self.groups = self.attrb['groups'].split(',')

        numAttrb = len(endptAttrb)
        for idx in range(0, len(endptParam)):
            self.param[endptParam[idx]] = row[numAttrb+idx]

    def repDict(self):
        rdList = []
        for idx in range(0, len(endptParam)):
            paramName = endptParam[idx]
            paramValue = self.param[paramName]
            if len(str(paramValue)) > 0:
                rd = {'paramObj': 'Endpoint', 'attributes': [], 'param': paramName, 'value': paramValue}
                for jdx in range(0, len(endptAttrb)):
                    attrbName = endptAttrb[jdx]
                    attrbValue = self.attrb[attrbName]
                    if len(str(attrbValue)) > 0:
                        attrbDict = {'attrbname': attrbName, 'attrbvalue' : attrbValue}
                        rd['attributes'].append(attrbDict)
                rdList.append(rd)              

        return rdList

    def validate(self):
        # endptAttrb = ('name', 'group', 'model', '*')
        # endptParam  = ('model', 'trace')
        global attrbDesc
 
        errs = []
        warnings = []

        trace = self.param['trace']
        valid, msg = validateBool(trace)
        if not valid:
            msg = 'error: Router param lists non-Boolean representation '"{}"' for trace parameter'.format(trace)
            errs.append(msg)
        else:
            self.param['trace'] = cnvrtBool(trace)

        if not validateFlag:
            return True, ""

        # warn if 
        #  - the endpt entry lists a endpt name not found in the attributes list
        #  - the endpt entry lists a group not found in the attributes list
        #  - the endpt entry lists a model not found in the attributes list
        # generate an error if
        #  - the endpt entry lists a model parameter that is not found in the system model
        
        attrbList = attrbDesc['Endpoint']

        endptName = self.attrb['name']
        endptModel = self.attrb['model']

        wildcard = self.attrb['*']

        if (isinstance(wildcard, str) and len(wildcard) > 0) or isinstance(wildcard, int):
            valid, msg = validateBool(wildcard)
            if not valid:
                msg = 'error: Endpoint attribute gives non-Boolean wildcard description "{}"'.format(wildcard)
                errs.append(msg)
            else:
                wcValue = cnvrtBool(wildcard)

                # if the wildcard is not true, clear it
                if wcValue == 0:
                    self.attrb['*'] = ''

        if len(endptName) > 0:
            nameFound = False
            for attrb in attrbList:
                if attrb['name'] == endptName:
                    nameFound = True
                    break
            if not nameFound:
                msg = 'warning: Endpoint attribute list gives endpt name "{}" not found in the system model'.format(endptName)
                warnings.append(msg)

        if len(endptModel) > 0:
            modelFound = False
            for attrb in attrbList:
                if attrb['model'] == endptModel:
                    modelFound = True
                    break
            if not modelFound:
                msg = 'warning: Endpoint attribute list gives endpt model "{}" not found in the system model'.format(endptModel)
                warnings.append(msg)

        if len(self.groups) > 0:
            groupsFound = {}
            for attrb in attrbList:
                if len(attrb['groups']) > 0:
                    for grp in attrb['groups']:
                        groupsFound[grp] = True

            # see if any group in self.group was not observed
            for grp in self.groups:
                if not grp in groupsFound:
                    msg = 'warning: Endpoint attribute list gives group name "{}" not found in the system model'.format(grp)
                    warnings.append(msg)

        # check the legality of the endpt parameters
        modelParam = self.param['model']
        if len(modelParam) > 0:
            modelFound = False
            for attrb in attrbList:
                if attrb['model'] == modelParam:
                    modelFound = True
                    break

            if not modelFound:
                msg = 'error: Endpoint parameter list gives endpt model "{}" not found in the system model'.format(modelParam)
                errs.append(msg)
        
        try:
            interrupt = float(self.param['interruptdelay'])
            if interrupt < 0.0:
                msg = 'error: Endpoint interruptdelay parameter ({}) needs to be non-negative (musecs)'.format(self.param['interruptdelay'])
                errs.append(msg)
        except:
                msg = 'error: Endpoint interruptdelay parameter ({}) needs to be non-negative (musecs)'.format(self.param['interruptdelay'])
                errs.append(msg)
        
        if len(warnings) > 0:
            for msg in warnings:
                print_err(msg)
          
        if len(errs) > 0:
            return False, '\n'.join(errs)

        return True, ""

class Interface:
    def __init__(self, row): 
        self.attrb = {}
        self.param = {}
        self.groups = []
 
        for idx in range(0, len(intrfcAttrb)):
            self.attrb[intrfcAttrb[idx]] = row[idx]

        if len(self.attrb['*']):
            self.attrb['*'] = cnvrtBool(self.attrb['*'])
            if self.attrb['*'] == 0:
                self.attrb['*'] = ''
 
        if len(self.attrb['groups']) > 0:
            self.groups = self.attrb['groups'].split(',')

        numAttrb = len(intrfcAttrb)
        for idx in range(0, len(intrfcParam)):
            try:
                self.param[intrfcParam[idx]] = row[numAttrb+idx]
            except:
                print('idx:{},len(intrfcParam):{},numAttrb+idx:{}, len(row):{}'.format(idx,len(intrfcParam),numAttrb+idx,len(row)))
                exit()

    def repDict(self):
        rdList = []
        for idx in range(0, len(intrfcParam)):
            paramName = intrfcParam[idx]
            paramValue = self.param[paramName]
            numericValue = isNumeric(paramValue)

            if len(str(paramValue)) > 0:
                # intrfcParam = ('latency', 'bandwidth', 'mtu', 'trace')
                if numericValue:
                    if paramName in ('latency'):
                        paramValue = float(paramValue)/1e6
                    if paramName in ('mtu'):
                        paramValue = int(mtu)

                if paramName in ('trace', 'detailedflow'):
                    paramValue = cnvrtBool(paramValue)
 
                rd = {'paramObj': 'Interface', 'attributes': [], 'param': paramName, 'value': paramValue}
                for jdx in range(0, len(intrfcAttrb)):
                    attrbName = intrfcAttrb[jdx]
                    attrbValue = self.attrb[attrbName]
                    if len(str(attrbValue)) > 0:
                        attrbDict = {'attrbname': attrbName, 'attrbvalue' : attrbValue}
                        rd['attributes'].append(attrbDict)
                
                rdList.append(rd)              

        return rdList

    def validate(self):
        # intrfcAttrb = ('name', 'group', 'devtype', 'devname', 'media', 'faces', '*')
        # intrfcParm  = ('latency', 'bandwidth', 'mtu', 'trace', 'detailedflow')
        errs = []
        warnings = []

        trace = self.param['trace']
        valid, msg = validateBool(trace)
        if not valid:
            msg = 'error: Interface param lists non-Boolean representation '"{}"' for trace parameter'.format(trace)
            errs.append(msg)
        else:
            self.param['trace'] = cnvrtBool(trace)

        detailedflow = self.param['detailedflow']
        valid, msg = validateBool(detailedflow)
        if not valid:
            msg = 'error: Interface param lists non-Boolean representation '"{}"' for detailed flow parameter'.format(trace)
            errs.append(msg)
        else:
            self.param['detailedflow'] = cnvrtBool(detailedflow)

        if not validateFlag:
            return True, ""

        devtype = self.attrb['devtype']
        devname = self.attrb['devname']
        media = self.attrb['media']
        faces = self.attrb['faces']
        wildcard = self.attrb['*']

        # warn if 
        #  - the intrfc entry lists a intrfc name not found in the attributes list
        #  - the intrfc entry lists a group not found in the attributes list
        #  - the intrfc entry lists a device name not found in the attributes list
        # generate an error if
        #  - latency or bandwidth are not non-negative reals
        #  - trace is not a boolean
        #  - MTU is not a non-negative integer
        #
        if (isinstance(wildcard, str) and len(wildcard) > 0) or isinstance(wildcard, int):
            valid, msg = validateBool(wildcard)
            if not valid:
                msg = 'error: Interface attribute gives non-Boolean wildcard description "{}"'.format(wildcard)
                errs.append(msg)
            else:
                self.attrb['*'] = cnvrtBool(self.attrb['*'])
                if self.attrb['*'] == 0:
                    self.attrb['*'] = ''

        if len(media) > 0 and media not in ('wired', 'wireless'):
            msg = 'error: Interface attribute list give unrecognized media type "{}"'.format(media)
            errs.append(msg)

        attrbList = attrbDesc['Interface']
        intrfcName = self.attrb['name']

        if len(intrfcName) > 0:
            nameFound = False
            for attrb in attrbList:
                if attrb['name'] == intrfcName:
                    nameFound = True
                    break
            if not nameFound:
                msg = 'warning: Interface attribute list gives intrfc name "{}" not found in the system model'.format(intrfcName)
                warnings.append(msg)

        if len(self.groups) > 0:
            groupsFound = {}
            for attrb in attrbList:
                if len(attrb['groups']) > 0:
                    for grp in attrb['groups']:
                        groupsFound[grp] = True

            # see if any group in self.group was not observed
            for grp in self.groups:
                if not grp in groupsFound:
                    msg = 'warning: Interface attribute list gives group name "{}" not found in the system model'.format(grp)
                    warnings.append(msg)

        if len(devtype) > 0:
            if devtype not in ('Switch', 'switch', 'Router', 'router', 'Endpoint', 'endpoint', 'endpt', 'Endpt'):
                msg = 'warning: Interface attribute list cites unrecognized device type "{}"'.format( devtype ) 
                warnings.append(msg)
    
        if len(media) > 0 and media not in ('wired', 'wireless'):
                msg = 'warning: Interface attribute list cites unrecognized media type "{}"'.format( media ) 
                warnings.append(msg)

        if len(faces) > 0:
            netFound = False
            for attrb in attrbList:
                if attrb['faces'] == faces:
                    netFound = True
                    break

            if not netFound:
                msg = 'warning: Interface attribute list gives network name "{}" the no system interface faces'.format(faces)
                warnings.append(msg)


        # check the legality of the intrfcwork parameters
        testParams = ('latency', 'bandwidth')
        for param in testParams:
            value = self.param[param]
            if len(value) == 0:
                continue
            if value.find('$') > -1:
                continue
            try:
                floatvalue = float(value)
                if floatvalue < 0.0:
                    msg = 'error: Interface param lists negative "{}"'.format(param)
                    errs.append(msg)
                elif param == 'latency':
                    self.param['latency'] = str(floatvalue/1e6)
            except:
                msg = 'error: Interface param lists non-floating point "{}"'.format(param)
                errs.append(msg)

        mtu = self.param['mtu']
        if len(mtu) > 0:
            if not mtu.isdigit():
                msg = 'Interface parameter specifies MTU value "{}" which is not an integer'.format(mtu)
                errs.append(msg)
            else:
                if int(mtu) < 0:
                    msg = 'Interface parameter specifies negative MTU value "{}"'.format(mtu)
                    errs.append(msg)

        if len(warnings) > 0:
            for msg in warnings:
                print_err(msg)
          
        if len(errs) > 0:
            return False, '\n'.join(errs)

        return True, ""

class Flow:
    def __init__(self, row):
        self.attrb = {}
        self.param = {}
        self.groups = []

        for idx in range(0, len(flowAttrb)):
            self.attrb[flowAttrb[idx]] = row[idx]

        if len(self.attrb['*']) > 0:
            self.attrb['*'] = cnvrtBool(self.attrb['*'])
            if self.attrb['*'] == 0:
                self.attrb['*'] = ''

        if len(self.attrb['groups']) > 0:
            self.groups = self.attrb['groups'].split(',')

        numAttrb = len(flowAttrb)
        for idx in range(0, len(flowParam)):
            self.param[flowParam[idx]] = row[numAttrb+idx]

        self.param['elastic'] = cnvrtBool(self.param['elastic'])

    def validate(self):
        msgs = []
        if len(self.param['elastic']) > 0:
            elastic = self.param['elastic']
            valid, msg = validateBool(elastic)
            if not valid:
                msg = 'error: Flow param lists non-Boolean representation '"{}"' for elastic parameter'.format(elastic)
                errs.append(msg)
            else:
                self.param['elastic'] = cnvrtBool(elastic)

            if not validateFlag:
                return True, ""

        attrbList = attrbDesc['Flow']
        srcdev    = self.attrb['srcdev']

        wildcard = self.attrb['*']

        if (isinstance(wildcard, str) and len(wildcard) > 0) or isinstance(wildcard, int): 
            valid, msg = validateBool(wildcard)
            if not valid:
                msg = 'error: Flow attribute gives non-Boolean wildcard description "{}"'.format(wildcard)
                errs.append(msg)
            else:
                wcValue = cnvrtBool(wildcard)

                # if the wildcard is not true, clear it
                if wcValue == 0:
                    self.attrb['*'] = ''

        if len(srcdev) > 0:
            nameFound = False
            for attrb in attrbList:
                if attrb['name'] == srcdev:
                    nameFound = True
                    break
            if not nameFound:
                msg = 'warning: flow attribute list gives srcdev name "{}" not found in the system model'.format(srcdev)
                warnings.append(msg)

        if len(dstdev) > 0:
            nameFound = False
            for attrb in attrbList:
                if attrb['name'] == dstdev:
                    nameFound = True
                    break
            if not nameFound:
                msg = 'warning: flow attribute list gives dstdev name "{}" not found in the system model'.format(dstdev)
                warnings.append(msg)

        if len(self.param['reqrate']) > 0:
            if not self.param['reqrate'].isnumeric():
                msg = 'error: flow param list give non numeric request rate "{}"'.format(self.param['reqrate'])
                msgs.append(msg) 
            else:
                reqrate = float(self.param['reqrate'])
                if reqrate < 0.0:
                    msg = 'error: flow param list give non numeric request rate "{}"'.format(self.param['reqrate'])
                    msgs.append(msg) 

        if len(self.param['classid']) > 0:
            if not self.param['classid'].isdigit():
                msg = 'error: flow param list give non integer class id "{}"'.format(self.param['classid'])
                msgs.append(msg) 
            else:
                classid = int(self.param['reqrate'])
                if classid < 0:
                    msg = 'error: flow param list give negative class id "{}"'.format(classid)
                    msgs.append(msg) 
        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""
        

    def repDict(self):
        rdList = []
        for idx in range(0, len(flowParam)):
            paramName = flowParam[idx]
            paramValue = self.param[paramName]
            if len(str(paramValue)) > 0:
                rd = {'paramObj': 'Flow', 'attributes': [], 'param': paramName, 'value': paramValue}
                for jdx in range(0, len(flowAttrb)):
                    attrbName = flowAttrb[jdx]
                    attrbValue = self.attrb[attrbName]
                    if len(attrbValue) > 0:
                        attrbDict = {'attrbname': attrbName, 'attrbvalue' : attrbValue}
                        rd['attributes'].append(attrbDict)
                
                rdList.append(rd)              

        return rdList
     

def validateNetworks():
    if not validateFlag:
        return True, ""

    msgs = []
    for net in networkList:
        valid, msg = net.validate()
        
        if not valid:
            msgs.append(msg)
    
    if len(msgs) > 0:
        return False, '\n'.join(msgs)
    return True, "" 

def validateSwitches():
    if not validateFlag:
        return True, ""

    msgs = []
    for switch in switchList:
        valid, msg = switch.validate()
        
        if not valid:
            msgs.append(msg)
    
    if len(msgs) > 0:
        return False, '\n'.join(msgs)
    return True, "" 

def validateRouters():
    if not validateFlag:
        return True, ""

    msgs = []
    for router in routerList:
        valid, msg = router.validate()
        
        if not valid:
            msgs.append(msg)
    
    if len(msgs) > 0:
        return False, '\n'.join(msgs)
    return True, "" 

def validateEndpoints():
    if not validateFlag:
        return True, ""

    msgs = []
    for endpt in endptList:
        valid, msg = endpt.validate()
        
        if not valid:
            msgs.append(msg)
    
    if len(msgs) > 0:
        return False, '\n'.join(msgs)
    return True, "" 

def validateInterfaces():
    if not validateFlag:
        return True, ""

    msgs = []
    for intrfc in intrfcList:
        valid, msg = intrfc.validate()
        
        if not valid:
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
    cell = row[0]
    if (cell.find('Unnamed') > -1  or cell.find('UnNamed') > -1 or cell.find('unnamed') > -1) :
        return True
    return False

def print_err(*a) : 
    print(*a, file=sys.stderr)


# called
def validateBool(v):
    if isinstance(v, int) and (v==0 or v==1):
        return True, ""

    if isinstance(v, str) and v.startswith('@'):
        return True, ""

    if isinstance(v, str) and v.startswith('$'):
        return True, ""

    if isinstance(v, str) and len(v) == 0:
        return True, ""

    if v in ('TRUE','True','true','yes','Yes','y','Y','T','t','1'):
        return True, ""
    if v in ('FALSE','False','false','F','f','no','N','No','n','0'):
        return True, ""
    return False, "error in boolean variable"

def cnvrtBool(v):
    if isinstance(v, int) and (v==0 or v==1):
        return v

    if isinstance(v, str) and v.startswith('@'):
        return v

    if isinstance(v, str) and v.startswith('$'):
        return v

    if isinstance(v, str) and len(v) == 0:
        return 0

    if v in ('TRUE','True','true','T','t','yes','Yes','y','Y'):
        return 1
    if v in ('FALSE','False','false','F','f','no','N','No','n'):
        return 0

    return v 

def validDev(devName):
    return devName in switchNames or devName in routerNames or devName in endptNames

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
    global attrbDesc, validateFlag

    global endptList, networkList, switchList, routerList, intrfcList, flowList

    parser = argparse.ArgumentParser()
    parser.add_argument(u'-name', metavar = u'name of system', dest=u'name', required=True)
    parser.add_argument(u'-validate', action='store_true', required=False)

    parser.add_argument(u'-csvDir', metavar = u'name of directory where csv inputs reside', dest=u'csvDir', required=True)
    parser.add_argument(u'-yamlDir', metavar = u'name of directory where result output resides', dest=u'yamlDir', required=True)
    parser.add_argument(u'-descDir', metavar = u'name of directory where description files reside', dest=u'descDir', required=True)

    # csv input file
    parser.add_argument(u'-csvIn', metavar = u'input csv file name', dest=u'csv_input', required=True)

    parser.add_argument(u'-attrbDescIn', metavar = u'input json file of attributes to use in validation', dest=u'attrbDesc_input', required=True)

    parser.add_argument(u'-devExecDescIn', metavar = u'input json file of device ops/functions to use in validation', dest=u'devExecDesc_input', required=True)
    # output file in the format of exp.yaml
    parser.add_argument(u'-exp', metavar = u'network parameter file name', dest=u'exp_output', required=True)

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
            errs.append('error: directory "{}" does not exist'.format(tdir))
        elif not directoryAccessible(tdir):
            errs.append('error: directory "{}" is not accessible'.format(tdir))

    if len(errs) > 0:
        for msg in errs:
            print(msg)
        exit(1)

    topoName  = args.name
    csv_input_file = os.path.join(csvDir, args.csv_input)
    exp_output_file = os.path.join(yamlDir, args.exp_output)
    attrbDescIn_file = os.path.join(descDir, args.attrbDesc_input)
    devExecDescIn_file = os.path.join(descDir, args.devExecDesc_input)

    errs = 0
    input_files = (csv_input_file, attrbDescIn_file, devExecDescIn_file)
    for input_file in input_files:
        if not os.path.isfile(input_file):
            print_err('unable to open input file "{}"'.format(input_file))
            errs += 1

    try: 
        with open(attrbDescIn_file, 'r') as rf:
            attrbDesc = json.load(rf)
    except:
        print_err('unable to open {}'.format(attrbDescIn_file))
        errs += 1

    try: 
        with open(devExecDescIn_file, 'r') as rf:
            devExecDesc = json.load(rf)
    except:
        print_err('unable to open {}'.format(devExecDescIn_file))
        errs += 1

    if errs > 0:
        exit(0)

    for actionName in devExecDesc['times']:
        actionDictList = devExecDesc['times'][actionName]
        for actionDict in actionDictList:
            if actionDict['devfunc'] == actionName:
                if actionName not in devFuncDict:
                    devFuncDict[actionName] = {}
                devFuncDict[actionName][actionDict['model']] = True
  
            if actionDict['devop'] == actionName:
                if actionName not in devOpDict:
                    devOpDict[actionName] = {}
                devOpDict[actionName][actionDict['model']] = True

    createIdx()

    network = False
    switch = False
    router  = False
    endpoint = False
    interface = False 
    
    msgs = []
    maxCols = 12
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

            row = cleanRow(row, maxCols)

            matchCode = "None"
            rowTypes = ('Network', 'Switch', 'Router', 'Endpoint', 'Interface', 'Flows') 
            for rowtype in rowTypes:
                if row[0].find(rowtype) > -1:
                    matchCode = rowtype 
           
            if matchCode == "Network": 
                    network = True
                    maxCols = 9
                    switch = False
                    router  = False
                    endpoint = False
                    interface = False 
                    flows = False
                    continue

            elif matchCode == "Switch": 
                    network = False
                    switch = True
                    maxCols = 8
                    router  = False
                    endpoint = False
                    interface = False 
                    flows = False
                    continue

            elif matchCode == "Router": 
                    network = False
                    switch = False
                    router  = True
                    maxCols = 8
                    endpoint = False
                    interface = False 
                    flows = False
                    continue

            elif matchCode == "Endpoint": 
                    network = False
                    switch = False
                    router  = False
                    endpoint = True
                    maxCols = 7
                    interface = False 
                    flows = False
                    continue

            elif matchCode == "Interface": 
                    network = False
                    switch = False
                    router  = False
                    endpoint = False
                    interface = True
                    maxCols = 12
                    flows = False
                    continue

            elif matchCode == "Flows": 
                    network = False
                    switch = False
                    router  = False
                    endpoint = False
                    interface = False
                    flows = True
                    maxCols = 8
                    continue


            row = row[:maxCols]

            if network:
                networkList.append(Network(row))
                continue

            if switch:
                switchList.append(Switch(row))
                continue


            if router:
                routerList.append(Router(row))
                continue


            if endpoint:
                endptList.append(Endpoint(row))
                continue


            if interface:
                intrfcList.append(Interface(row))
                continue

            if flows:
                flowList.append(Flow(row))
                continue

    msgs = []
    statements = []
    valid, msg = validateNetworks()
    if not valid:
        msgs.append(msg)

    valid, msg = validateSwitches()
    if not valid:
        msgs.append(msg)

    valid, msg = validateRouters()
    if not valid:
        msgs.append(msg)

    valid, msg = validateEndpoints()
    if not valid:
        msgs.append(msg)

    valid, msg = validateInterfaces()
    if not valid:
        msgs.append(msg)

    if len(msgs) > 0:
        for msgrp in msgs:
            msgList = msgrp.split('\n')
            for msg in msgList:
                print_err(msg)
        exit(1)

    for net in networkList:
        netStatements = net.repDict()
        statements.extend(netStatements)

    for switch in switchList:
        switchStatements = switch.repDict()
        statements.extend(switchStatements)

    for router in routerList:
        routerStatements = router.repDict()
        statements.extend(routerStatements)

    for endpt in endptList:
        endptStatements = endpt.repDict()
        statements.extend(endptStatements)

    for intrfc in intrfcList:
        intrfcStatements = intrfc.repDict()
        statements.extend(intrfcStatements)

    for flow in flowList:
        flowStatements = flow.repDict()
        statements.extend(flowStatements)

    expDict = {'expname': topoName, 'parameters': statements}
    with open(exp_output_file, 'w') as wf:
        yaml.dump(expDict, wf, default_flow_style=False)

def cleanRow(row, mxc):
    rtn = []
    commented = False
    for r in row:
        if r.startswith('#!'):
            r = ''                     
            commented = True
        elif len(rtn) > 0 and r.startswith('#'):
            commented = True
            break

        rtn.append(r)

    residual = mxc-len(rtn)
    if not commented and residual > 0 :
        for idx in range(0,residual):
            rtn.append('')

    return rtn

def isNumeric(v):
    if isinstance(v,int) or isinstance(v,float):
        return True
    if isinstance(v,str) and v.isnumeric():
        return True
    try:
        x = float(v)
        return True
    except:
        return False



if __name__ == '__main__':
    main()

