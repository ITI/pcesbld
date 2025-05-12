#!/usr/bin/env python

import csv
import pdb
import yaml
import json
import sys
import os
import argparse


# Globals
funcInstByName = {}
cmpPtnInstDict = {}
cmpPtnInstByName = {}
sysCP = {}
cpnames = []
cptypes = {}
initClassDict = {}
cpFuncs = {}
cpInstDict = {}
cpMC = {}
edgeMsg = {}

mcodes = {"processPckt":["default","processOp"], "finish":["default","finishOp"], "measure":["default","measure"], 
    "srvRsp":["default"], "srvReq":["default", "request","return"], "transfer":["default"], "authReq":["default"], 
    "bckgrndLd":[], "transfer":[], "streamsrc":[], "streamdst":[]}

messages = {}
classFuncs = {}
srvOpDict = {}

validateFlag = True

allOps = []

patternDict = {} 
connectionList = []

cmpptnDesc = {}

pcesFuncClasses = ('srvReq', 'srvRsp', 'measure', 'start', 'finish', 'bckgrndLd', 
                        'processPckt', 'transfer', 'streamsrc', 'streamdst')

TimingCodeFuncs = []

strmSrcIdx = {}
strmSrcIdx['empty'] = 0
strmSrcIdx['srccmpptn'] = 1
strmSrcIdx['srclabel'] = len(strmSrcIdx)
strmSrcIdx['dstcmpptn'] = len(strmSrcIdx)
strmSrcIdx['dstlabel'] = len(strmSrcIdx)
strmSrcIdx['name'] = len(strmSrcIdx)
strmSrcIdx['pcktstrm'] = len(strmSrcIdx)
strmSrcIdx['reqrate'] = len(strmSrcIdx)
strmSrcIdx['msgtype'] = len(strmSrcIdx)
strmSrcIdx['msglen'] = len(strmSrcIdx)
strmSrcIdx['elastic'] = len(strmSrcIdx)
strmSrcIdx['start'] = len(strmSrcIdx)
strmSrcIdx['volume'] = len(strmSrcIdx)
strmSrcIdx['burstdist'] = len(strmSrcIdx)
strmSrcIdx['flowmodel'] = len(strmSrcIdx)
strmSrcIdx['pause'] = len(strmSrcIdx)
strmSrcIdx['cycles'] = len(strmSrcIdx)
strmSrcIdx['data'] = len(strmSrcIdx)
strmSrcIdx['groups'] = len(strmSrcIdx)
strmSrcIdx['trace'] = len(strmSrcIdx)

strmDstIdx = {}
strmDstIdx['empty'] = 0
strmDstIdx['dstcmpptn'] = len(strmDstIdx)
strmDstIdx['dstlabel'] = len(strmDstIdx)
strmDstIdx['srccmpptn'] = len(strmDstIdx)
strmDstIdx['srclabel'] = len(strmDstIdx)
strmDstIdx['name'] = len(strmDstIdx)
strmDstIdx['pcktstrm'] = len(strmDstIdx)
strmDstIdx['data'] = len(strmDstIdx)
strmDstIdx['groups'] = len(strmDstIdx)
strmDstIdx['trace'] = len(strmDstIdx)

initRowLen = {}
initRowLen['srvReq'] = 14
initRowLen['srvRsp'] = 10
initRowLen['measure'] = 9
initRowLen['start'] = 10
initRowLen['finish'] = 8
initRowLen['processPckt'] = 12
initRowLen['transfer'] = 11
initRowLen['streamsrc'] = 21
initRowLen['streamdst'] = 10

class FuncEdge:
    def __init__(self, cp, label, msgType):
        self.cp = cp
        self.label = label
        self.msgType = msgType
        
class FuncInst:
    def __init__(self, cmpPtnName, className, funcName):
        self.cmpPtnName = cmpPtnName
        self.className = className
        self.funcName  = funcName
        self.inEdges = []
        self.outEdges = []
 
    def addInEdge(self, cp, label, msgType):
        self.inEdges.append(FuncEdge(cp,label, msgType))
 
    def addOutEdge(self, cp, label, msgType):
        self.outEdges.append(FuncEdge(cp,label, msgType))

    def msgOnInEdge(self, msgType):
        # response functions can be called without an in edge
        if self.className == 'srvRsp':
            return True, ""

        for edge in self.inEdges:
            if edge.msgType == msgType or msgType == "default":
                return True, ""
        return False, 'expected msg with type "{}" on cp "{}" function "{}" inedge'.format(msgType, self.cmpPtnName, self.funcName)

    def validate(self):
        if not validateFlag:
            return True, ""

        # no validation to be done on function name 
        if self.className in pcesFuncClasses:
            return True, ""
        return False, 'in funcInst.validate function class "{}" not observed in pces'.format(self.className)
  
class CmpPtnInst:
    def __init__(self, name, cpType):
        self.name = name
        self.cpType = cpType
        self.funcInstList = []
        self.services = {}
        cmpPtnInstDict[name] = self
        funcInstByName[name] = {}
        cmpPtnInstByName[name] = self

    def addFunc(self, func):
        self.funcInstList.append(func)  
        funcInstByName[self.name][func.funcName] = func

 
    def addService(self, srvOp, funcDesc):
        pieces = funcDesc.split(',') 
        if len(pieces) == 2:
            cpName = pieces[0].strip()
            funcName = pieces[1].strip()
        else:
            cpName = ""
            funcName = pieces[0].strip()

        self.services[srvOp] = (cpName, funcName)
        srvOpDict[srvOp] = True


    def validate(self):
        if not validateFlag:
            return True, ""
        msgs = []
        for func in self.funcInstList:
            validated, msg = func.validate()
            if not validated:
                msgs.append(msg)

        # check that function labels are not duplicated
        funcHere = {}
        for func in self.funcInstList:
            if func.funcName in funcHere:
                msgs.append('duplicated function "{}" in declaration of CP "{}"'.format(func.funcName, self.name))

        if len(self.services) > 0:
            # check that function codes for service are present
            #for _, srvFuncName in self.services.items():
            for _, srvPair in self.services.items():
                found = False
                srvCPName = srvPair[0]
                srvFuncName = srvPair[1]
                if len(srvCPName) == 0:
                    srvCPName = self.name
                    for func in self.funcInstList:
                        if func.funcName == srvFuncName:
                            found = True
                            break
                else:
                    if srvCPName not in cmpPtnInstByName:
                        msg = 'service CP name "{}" not found in system model'.format(srvCPName)
                        msgs.append(msg)
                    else:
                        cpi = cmpPtnInstByName[srvCPName]
                        for func in cpi.funcInstList:
                            if func.funcName == srvFuncName:
                                found = True
                                break

                if not found:
                    msgs.append('service function "{}" expected in cp "{}"'.format(srvFuncName, srvCPName)) 

        if len(msgs) > 0:
            return False, '\n'.join(msgs)
        return True, ""
   
    def funcExists(self, fname):
        for func in self.funcInstList:
            if func.funcName == fname:
                return True,""

        return False, 'expected func "{}" within comp pattern instance "{}"'.format(fname, self.name)   

    def getFuncInst(self, fname):
        for func in self.funcInstList:
            if func.funcName == fname:
                return func
       
        return None

    def repDict(self):
        sd = {'cptype': self.cpType , 'name': self.name, 'funcs': [], 'edges': [],  \
                    'extedges':[], 'services': {}}

        for func in self.funcInstList:
            fd = {'class': func.className, 'label': func.funcName}
            sd['funcs'].append(fd)

        for key, value in self.services.items():
            sd['services'][key] = {'cp': value[0], 'label':value[1]}

        # go through all the edges listed in connectionsList and pick out those have this comp pattern as source
        for conn in connectionList:

            if conn.srcCP != self.name:
                continue

            edge = {'srccp': conn.srcCP, 'dstcp': conn.dstCP, 'srclabel': conn.srcLabel, 'dstlabel': conn.dstLabel, \
                        'msgtype': conn.msgType}

            if conn.dstCP == conn.srcCP:
                sd['edges'].append(edge)
            else:
                sd['extedges'].append(edge)

        return sd

    def repFuncs(self):
        dd = []
        for func in self.funcInstList:
            dd.append(func.funcName)

        return dd

class Connection():
    def __init__(self, srcCP, dstCP, srcLabel, dstLabel, msgType):
        self.srcCP = srcCP
        self.dstCP = dstCP
        self.srcLabel = srcLabel
        self.dstLabel = dstLabel
        self.msgType = msgType

        # add the in and out edges to the functions
        msgs = []
        
        srccp_present = (self.srcCP=="*") or (self.srcCP in funcInstByName)
        if not srccp_present:
            msg = 'Connection srcCP "{}" is not defined'.format(self.srcCP)
            msgs.append(msg)
        else:
            labelpresent =  (self.srcLabel=="*") or (self.srcLabel in funcInstByName[self.srcCP])
            if not labelpresent:
                msg = 'Connection srcCP "{}" srcLabel "{}" is not defined'.format(self.srcCP, self.srcLabel)
                msgs.append(msg)
            elif self.srcCP != "*":
                src_cpfi =  funcInstByName[self.srcCP][self.srcLabel]

        dstcp_present = (self.dstCP in funcInstByName)
        if not dstcp_present:
            msg = 'Connection dstCP "{}" is not defined'.format(self.dstCP)
            msgs.append(msg)
        else:
            labelpresent =  (self.dstLabel in funcInstByName[self.dstCP])
            if not labelpresent:
                msg = 'Connection dstCP "{}" dstLabel "{}" is not defined'.format(self.dstCP, self.dstLabel)
                msgs.append(msg)
            else:
                dst_cpfi =  funcInstByName[self.dstCP][self.dstLabel]

        if len(msgs) > 0:
            for msg in msgs:
                print_err(msg)
            exit(1)
 
        # CP and lables are vetted, src_cpfi and dst_cpfi are set.

        if self.srcCP != "*": 
            src_cpfi.addOutEdge(self.dstCP, self.dstLabel, self.msgType)
        dst_cpfi.addInEdge(self.srcCP, self.srcLabel, self.msgType)

        if srcCP != "*":
            if srcCP not in messages:
                messages[srcCP] = {}
            messages[srcCP][self.msgType] = True


    def validate(self):
        if not validateFlag:
            return True, ""

        if self.srcCP != "*" and self.srcCP not in cmpPtnInstDict:
            return False, 'expected definition of comp pattern "{}"'.format(self.srcCP)

        if self.dstCP not in cmpPtnInstDict:
            return False, 'expected definition of comp pattern "{}"'.format(self.dstCP)

        msgs = [] 
        if self.srcCP != "*" and self.srcLabel != "*":
            cpi = cmpPtnInstDict[self.srcCP]  

            present, msg = cpi.funcExists(self.srcLabel)
            if not present:
                msgs.append(msg)

        cpi = cmpPtnInstDict[self.dstCP]  
        present, msg = cpi.funcExists(self.dstLabel)
        if not present:
            msgs.append(msg)

        if len(self.msgType) == 0:
            msg = 'expected message type in connection from ({}, {}) to ({}, {})'.format(
                self.srcCP, self.srcLabel, self.dstCP, self.dstLabel)   
            msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)
        return True, ""

class SrvReq:
    def __init__(self, row):
        self.cmpptn = row[1]
        self.label = row[2]
        self.init = {}
        self.init['trace']  = row[3] 
        self.init['srvCP'] =  row[6] 
        self.init['srvLabel'] = row[7]
        self.init['srvOp'] = row[8] 
        self.init['rspOp'] = row[9]
        self.init['msg2mc'] = {} 
        self.init['msg2msg'] = {} 
        self.init['groups'] = []

    def addGroup(self, groupName):
        if 'groups' not in self.init:
            self.init['groups'] = []
        if groupName not in self.init['groups']:
            self.init['groups'].append(groupName)

    def validate(self):
        if not validateFlag:
            return True, ""

        if self.cmpptn not in cmpPtnInstDict:
            msg = 'cp name "{}" in SrvReq init not recognized'.format(self.cmpptn)
            return False, msg 

        if len(self.init['srvCP']) >0  and self.init['srvCP'] not in cmpPtnInstDict:
            msg = 'service cp name "{}" in requesting function not recognized'.format(self.init['srvCP'])
            return False, msg 

        msgs = []
        if not validateBool(self.init['trace']):
            msg = 'SrvReq trace parameter "{}" needs to be a boolean'.format(self.init['trace'])
            msgs.append(msg)

        ok, msg = validateFuncInCP(self.cmpptn, self.label, "srvReq init validation")
        if not ok:
            msgs.append(msg) 

        if len(msgs) == 0:
            # determine whether there is an outedge to a srvRsp function
            cpi = cmpPtnInstDict[self.cmpptn]  
            cpfi = cpi.getFuncInst(self.label)
            srvRspFound = None
            for edge in cpfi.outEdges:
                xcpi = cmpPtnInstDict[edge.cp]
                xcpfi = xcpi.getFuncInst(edge.label)
                if xcpfi.className == 'srvRsp':
                    srvRspFound = edge
                    break

            # problem if the service CP is given and there is an edge to a service function
            # but not in the CP described in srvCP
            if srvRspFound is not None and len(self.init['srvCP']) > 0 and srvRspFound.cp != self.init['srvCP']: 
                msg = 'srvReq function ("{}","{}") has conflict between srvCP and CP on edge to srvRsp function'.format(self.cmpptn, self.label)
                msgs.append(msg)

            elif srvRspFound is not None and srvRspFound.label != self.init['srvLabel'] :
                msg = 'srvReq function ("{}","{}") has conflict between srvLabel and Label on edge to srvRsp function'.format(self.cmpptn, self.label)
                msgs.append(msg)

            if srvRspFound is None: 
                # problem if no service CP given nor edge to a comp pattern that provides the service
                if len(self.init['srvOp']) == 0:
                    msg = 'srvReq function ("{}","{}") does not provide direction to a service Op'.format(self.cmpptn, self.label)
                    msgs.append(msg)


                # problem if service CP given but that CP's list of services does not include self.init['srvOp']
                srvCP = self.init['srvCP']
                srvLabel = self.init['srvLabel']

                # if exactly one or the other of the srvCP or srvLabel are empty there is a problem
                bypass = False
                if (len(srvCP) == 0 and len(srvLabel) > 0) or (len(srvCP) >0 and len(srvLabel) == 0):
                    msg = 'srvReq service specification ({}, {}) requires srvCP and srvLabel to both be empty, or both be non-empty'.format(srvCP, srvLabel)
                    msgs.append(msg)
                    bypass = True

                if not bypass and len(srvCP) > 0:
                    if not srvCP in cmpPtnInstDict:
                        msg = 'srvReq lists cmpptn srvCP "{}" that does not exist in the model'.format(srvCP)
                        msgs.append(msg)
                    else:
                        xcpi = cmpPtnInstDict[srvCP]
                        # if a source label is given check that that function is known

                        if len(srvLabel) > 0 :
                            xcpfi = xcpi.getFuncInst(srvLabel)
                            if xcpfi is None:
                                msg = 'srvReq lists srvLabel {} for cmpptn srvCP "{}" that does not exist in the model'.format(srvLabel, srvCP)
                                msgs.append(msg)
                        else:
                            # srvLabel is empty, which means we go to the services table of the srvCP
                            # only prefixes are listed in services
                            pieces = self.init['srvOp'].split('-')
                            if pieces[0] not in xcpi.services:
                                msg = 'srvReq lists srvOp prefix {} not found in the services table of server cmpptn {}'.format(pieces[0], srvCP)
                                msgs.append(msg)


        if len(msgs) > 0:
            return False, '\n'.join(msgs)
        return True, ""

    def addMsg2MC(self, msgType, mc):
        self.init['msg2mc'][msgType] = mc

    def addMsg2Msg(self, msgTypeIn, msgTypeOut):
        self.init['msg2msg'][msgTypeIn] = msgTypeOut 

    def serializeDict(self):
        self.init['trace']  = cnvrtBool(self.init['trace'])
        return self.init

class SrvRsp:
    def __init__(self, row):
        self.cmpptn = row[1]
        self.label = row[2]
        self.init = {'timingcode': {}, 'directprefix':[], 'trace': row[6], 'msg2mc':{}, 'groups':[] }
 
    def addTimingCode(self, mc, tc):
        self.init['timingcode'][mc] = tc

    def addDirectPrefix(self, prefix):
        self.init['directprefix'].append(prefix)

    def addGroup(self, groupName):
        if groupName not in self.init:
            self.init['groups'].append(groupName)


    def validate(self):

        # remember this function if it has an interesting timing code dictionary
        if len(self.init['timingcode']) > 0:
            TimingCodeFuncs.append(self)

        if not validateFlag:
            return True, ""

        if self.cmpptn not in cmpPtnInstDict:
            print_err('cp name "{}" in SrvRsp init not recognized'.format(self.cmpptn))
            exit(1)

        msgs = []
        if not validateBool(self.init['trace']):
            msg = 'SrvRsp initialization trace parameter "{}" needs to be boolean'.format(self.init['trace'])
            msgs.append(msg)

        if not validateBool(self.init['trace']):
            msg = 'Trace in SrvRsp init not a Bool'.format(self.init['trace'])
            msgs.append(msg) 

        ok, msg = validateFuncInCP(self.cmpptn, self.label,"srvRsp init validation")
        if not ok:
            msgs.append(msg)

        # the key of timing code is inbound message type
        for mc, fc in self.init['timingcode'].items():
            # check if timing code key is the msgType on an input edge
            # to the function being initialized.  Not necessary if
            # the function is a server (type srvRsp) and the timing
            # code is in the CP's services table

            if self.cmpptn not in cmpPtnInstByName:
                msg = 'srvRsp init cites cmpptn "{}" that does not exist'.format(self.cmpptn)
                msgs.append(msg)
            else: 
                cpi = cmpPtnInstByName[self.cmpptn]
                cpfi = cpi.getFuncInst(self.label)
                if cpfi is None:
                    msg = 'srvRsp init cites function ({},{}) that does not exist'.format(self.cmpptn, self.label)
                    msgs.append(msg)
                else: 
                    if not (cpfi.className == 'srvRsp' and mc in cpi.services):
                        ok, msg = cpfi.msgOnInEdge(mc)
                        if not ok:
                            msgs.append(msg)

                    if fc not in allOps:
                        msg = 'expected function operation code "{}" to be found in list from function/device timing table'.format(fc)
                        msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def addMsg2MC(self, msgType, mc):
        self.init['msg2mc'][msgType] = mc

    def repTC(self):
        self.init['cmpptn'] = self.cmpptn
        self.init['label'] = self.label
        return self.init

    def serializeDict(self):
        self.init['trace'] = cnvrtBool(self.init['trace'])
        return self.init

class Measure:
    def __init__(self, row):
        self.cmpptn = row[1]
        self.label = row[2]
        self.init = {'msrname': row[3], 'msrop': row[4], 'trace': row[5], 'msg2mc': {}, 'groups':[]}

    def addGroup(self, groupName):
        if 'groups' not in self.init:
            self.init['groups'] = []
        if groupName not in self.init['groups']:
            self.init['groups'].append(groupName)


    def validate(self):
        if not validateFlag:
            return True, ""

        if self.cmpptn not in cmpPtnInstDict:
            print_err('cp name "{}" in Measure init not recognized'.format(self.cmpptn))
            exit(1)

        msgs = []
        if not validateBool(self.init['trace']):
            msg = 'Measure trace parameter "{}" needs to be a boolean'.format(self.init['trace'])
            msgs.append(msg)


        ok, msg = validateFuncInCP(self.cmpptn,  self.label, "measure init validation")
        if not ok:
            msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def addMsg2MC(self, msgType, mc):
        self.init['msg2mc'][msgType] = mc

    def serializeDict(self):
        self.init['trace'] = cnvrtBool(self.init['trace'])
        return self.init

class Start:
    def __init__(self, row):
        self.cmpptn = row[1]
        self.label = row[2]
        self.init = {'pcktlen': row[3], 'msglen': row[4], 'msgtype': row[5],
                         'starttime': row[6], 'data': row[7], 
                            'groups':[], 'trace': row[8]} 

    def addGroup(self, groupName):
        if 'groups' not in self.init:
            self.init['groups'] = []
        if groupName not in self.init['groups']:
            self.init['groups'].append(groupName)

    def validate(self):
        if not validateFlag:
            return True, ""
 
        msgs = []
        msg = 'Start initialization starttime parameter "{}" needs to be non-negative float'.format(self.init['starttime'])
        if not self.init['starttime'].isnumeric():  
            msgs.append(msg)
        else:   
            starttime = float(self.init['starttime'])
            if starttime < 0.0:
                msgs.append(msg)
        
        if not validateBool(self.init['trace']):
            msg = 'Start initialization trace parameter "{}" needs to be boolean'.format(self.init['trace'])
            msgs.append(msg)           

   
        if self.cmpptn not in cmpPtnInstDict:
            msg = 'cp name "{}" in Finish init not recognized'.format(self.cmpptn)
            msgs.append(msg) 
        else: 
            ok, msg = validateFuncInCP(self.cmpptn, self.label,"finish init validation")
            if not ok:
                msgs.append(msg)

        # check lengths of pckt and msg
        if validateFlag and (not (0 <= int(self.init['pcktlen']) < 1560) or \
                not (0 <= int(self.init['msglen']) < 1560) or \
                not (int(self.init['pcktlen']) <= int(self.init['msglen']))) :

            msg = 'initial pckt or msg length size problem'
            msgs.append(msg)


        if validateFlag:
            try:
                starttime = float(self.init['starttime'])
            except:
                msg = 'start function gives non floating point start time {}'.format(self.init['starttime'])
                msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def serializeDict(self):
        self.init['trace'] = cnvrtBool(self.init['trace'])
        if isinstance(self.init['starttime'], str) and self.init['starttime'].find('$') == -1:
            self.init['starttime'] = float(self.init['starttime'])
        if isinstance(self.init['pcktlen'], str) and self.init['pcktlen'].find('$') == -1:
            self.init['pcktlen'] = int(self.init['pcktlen'])
        if isinstance(self.init['msglen'], str) and self.init['msglen'].find('$') == -1:
            self.init['msglen'] = int(self.init['msglen'])
        if 'data' in self.init:
            if self.init['data'].startswith('float('):
                self.init['data'] = self.init['data'].replace('float(','str(')
            elif self.init['data'].startswith('int('):
                self.init['data'] = self.init['data'].replace('int(','str(')
            else:
                self.init['data'] = self.init['data'].replace('"','')
                self.init['data'] = str(self.init['data'])

        comment = '''
        if len(self.init['data']) > 0:
            data = self.init['data']
            if data.startswith('int('):
                data = data[4:]
                end = data.find(')')
                data = data[:end]
            elif data.startswith('float('):
                data = data[6:]
                end = data.find(')')
                data = data[:end]
            elif data.startswith('bool('):
                data = data[5:]
                end = data.find(')')
                data = data[:end]
            data = "str("+data+")"
            self.init['data'] = data 
        '''
        self.init['data'] = str(self.init['data'])
        return self.init

class Finish:
    def __init__(self, row):
        self.cmpptn = row[1]
        self.label = row[2]
        self.init = {'trace': row[3], 'msg2mc': {}, 'data': row[6], 'groups':[]} 

    def addGroup(self, groupName):
        if 'groups' not in self.init:
            self.init['groups'] = []
        if groupName not in self.init['groups']:
            self.init['groups'].append(groupName)

    def validate(self):
        if not validateFlag:
            return True, ""

        if self.cmpptn not in cmpPtnInstDict:
            print_err('cp name "{}" in Finish init not recognized'.format(self.cmpptn))
            exit(1)
    
        msgs = []
        ok, msg = validateFuncInCP(self.cmpptn, self.label,"finish init validation")
        if not ok:
            msgs.append(msg)

        if not validateBool(self.init['trace']):
            msg = 'finish initialization trace parameter "{}" needs to be boolean'.format(self.init['trace'])
            msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def addMsg2MC(self, msgType, mc):
        self.init['msg2mc'][msgType] = mc

    def serializeDict(self):
        self.init['trace'] = cnvrtBool(self.init['trace'])
        self.init['data'] = str(self.init['data'])
        return self.init

class StreamSrc:
    def __init__(self, row):
        self.init = {'groups': []}
        for field, idx in strmSrcIdx.items():
            if idx==0:
                 continue

            if field != 'groups':
                self.init[field] = row[idx]
            elif len(row[idx]) > 0:
                self.init['groups'].append(row[idx])

    def validate(self):
        if not validateFlag:
            return True, ""

        msgs = []
        if self.init['srccmpptn'] not in cmpPtnInstDict:
            print_err('src cp name "{}" in StreamSrc not recognized'.format(self.init['srccmpptn']))
            exit(1)

        if self.init['dstcmpptn'] not in cmpPtnInstDict:
            print_err('dst cp name "{}" in StreamSrc not recognized'.format(self.init['dstcmpptn']))
            exit(1)

        cmpptn = self.init['srccmpptn']
        label  = self.init['srclabel']

        ok, msg = validateFuncInCP(cmpptn, label, 'StreamSrc names unknown stream label "{}"'.format(label))
        if not ok:
            msgs.append(msg)

        cpi = cmpPtnInstByName[cmpptn]
        if cpi is None:
            msg = 'in StreamSrc no comp pattern with name "{}" is defined'.format(cmpptn)
            msgs.append(msg)
        else:
            cpfi = cpi.getFuncInst(self.init['srclabel'])
            if cpfi is None:
                msg = 'in StreamSrc no function label "{}" in CP "{}"'.format(label, cmpptn)
                msgs.append(msg)

        cmpptn = self.init['dstcmpptn']
        label  = self.init['dstlabel']

        ok, msg = validateFuncInCP(cmpptn, label, 'StreamSrc names unknown stream label "{}"'.format(label))
        if not ok:
            msgs.append(msg)

        cpi = cmpPtnInstByName[cmpptn]
        if cpi is None:
            msg = 'in StreamSrc no comp pattern with name "{}" is defined'.format(cmpptn)
            msgs.append(msg)
        else:  
            cpfi = cpi.getFuncInst(self.init['dstlabel'])
            if cpfi is None:
                msg = 'in StreamSrc no function label "{}" in CP "{}"'.format(label, cmpptn)
                msgs.append(msg)

        floats = ('reqrate', 'start', 'volume', 'pause')
        for key in floats:
            msg = ""
            try:
                x = float(self.init[key])
                if x < 0.0:
                    msg = 'StreamSrc {} "{}" needs to be non-negative'.format(key, x)
            except: 
                    msg = 'StreamSrc {} "{}" needs to be non-negative float'.format(key, self.init[key])
               
            if len(msg) > 0:
                msgs.append(msg)

        ints = ('msglen', 'cycles')
        for key in ints:
            msg = ""
            if len(self.init[key])==0:
                self.init[key]=0
            try:
                x = int(self.init[key])
                if x < 0:
                    msg = 'StreamSrc {} "{}" needs to be non-negative'.format(key, x)
            except: 
                    msg = 'StreamSrc {} "{}" needs to be non-negative int'.format(key, self.init[key])
               
            if len(msg) > 0:
                msgs.append(msg)

        bools = ('pcktstrm', 'elastic', 'trace')
        for key in bools:
            if not validateBool(self.init[key]):
                msg = 'StreamSrc {} "{}" needs to be boolean'.format(key, self.init[key])
                msgs.append(msg)


        # with a flow model selection the code must be in {'const','exponential'}
        if len(self.init['flowmodel']) > 0:
            fm = self.init['flowmodel'].strip()
            if fm not in {'const','exp','exponential','expon'}:   
                msg = 'StreamSrc flowmodel code {} needs to be in ("const","exp","expon", "exponential")'.format(fm)
                msgs.append(msg)
 
        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def addGroup(self, groupName):
        if 'groups' not in self.init:
            self.init['groups'] = []
        if groupName not in self.init['groups']:
            self.init['groups'].append(groupName)

    def serializeDict(self):
        self.init['trace'] = cnvrtBool(self.init['trace'])
        self.init['pcktstrm'] = cnvrtBool(self.init['pcktstrm'])
        self.init['elastic'] = cnvrtBool(self.init['elastic'])

        floats = ('reqrate', 'start', 'volume', 'pause')
        for key in floats:
            if isinstance(self.init[key],str) and self.init[key].find('$') == -1:
                self.init[key] = float(self.init[key])

        ints = ('msglen', 'cycles')
        for key in ints:
            if isinstance(self.init[key],str) and self.init[key].find('$') == -1 and len(self.init[key]) > 0:
                self.init[key] = int(self.init[key])
            else:
                self.init[key] = 0

        return self.init

class StreamDst:
    def __init__(self, row):
        self.init = {'groups': []}
        for field, idx in strmDstIdx.items():
            if idx==0:
                 continue
            if field != 'groups':
                self.init[field] = row[idx]
            elif len(row[idx]) > 0:
                self.init['groups'].append(row[idx])

    def validate(self):
        if not validateFlag:
            return True, ""

        msgs = []

        if self.init['srccmpptn'] not in cmpPtnInstDict:
            print_err('src cp name "{}" in StreamDst not recognized'.format(self.init['srccmpptn']))
            exit(1)

        if self.init['dstcmpptn'] not in cmpPtnInstDict:
            print_err('dst cp name "{}" in StreamDst not recognized'.format(self.init['dstcmpptn']))
            exit(1)

        cmpptn = self.init['srccmpptn']
        label  = self.init['srclabel']

        ok, msg = validateFuncInCP(cmpptn, label, 'StreamDst names unknown stream label "{}"'.format(label))
        if not ok:
            msgs.append(msg)

        cpi = cmpPtnInstByName[cmpptn]
        if cpi is None:
            msg = 'in StreamDst no comp pattern with name "{}" is defined'.format(cmpptn)
            msgs.append(msg)
        else:  
            cpfi = cpi.getFuncInst(self.init['srclabel'])
            if cpfi is None:
                msg = 'in StreamDst no function label "{}" in CP "{}"'.format(label, cmpptn)
                msgs.append(msg)

        cmpptn = self.init['dstcmpptn']
        label  = self.init['dstlabel']

        ok, msg = validateFuncInCP(cmpptn, label, 'StreamDst names unknown stream label "{}"'.format(label))
        if not ok:
            msgs.append(msg)

        cpi = cmpPtnInstByName[cmpptn]
        if cpi is None:
            msg = 'in StreamDst no comp pattern with name "{}" is defined'.format(cmpptn)
            msgs.append(msg)
        else:  
            cpfi = cpi.getFuncInst(self.init['dstlabel'])
            if cpfi is None:
                msg = 'in StreamDst no function label "{}" in CP "{}"'.format(label, cmpptn)
                msgs.append(msg)

        bools = ('pcktstrm', 'trace')
        for key in bools:
            if not validateBool(self.init[key]):
                msg = 'StreamDst {} "{}" needs to be boolean'.format(key, self.init[key])
                msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def addGroup(self, groupName):
        if 'groups' not in self.init:
            self.init['groups'] = []
        if groupName not in self.init['groups']:
            self.init['groups'].append(groupName)

    def serializeDict(self):
        self.init['trace'] = cnvrtBool(self.init['trace'])
        self.init['pcktstrm'] = cnvrtBool(self.init['pcktstrm'])
        return self.init

class BckgrndLd:
    def __init__(self, row):
        self.cmpptn = row[1]
        self.label = row[2]
        self.init = {'bckgrndfunc': row[3], 'bckgrndrate': row[4], 
                         'bckgrndsrv': row[5], 'trace': row[6], 'msg2mc': {}, 'groups':[]} 

    def addGroup(self, groupName):
        if 'groups' not in self.init:
            self.init['groups'] = []
        if groupName not in self.init['groups']:
            self.init['groups'].append(groupName)

    def validate(self):
        if not validateFlag:
            return True, ""

        if self.cmpptn not in cmpPtnInstDict:
            print_err('cp name "{}" in BckgrndLd not recognized'.format(self.cmpptn))
            exit(1)

        msgs = []
        ok, msg = validateFuncInCP(self.init['cmpptn'], self.init['label'],"bckgrndLd init validation")
        if not ok:
            msgs.append(msg)
  
        if len(self.init['bckgrndrate']) > 0:
            bgr = self.init['bckgrndrate']
            msg = 'bckgrndLd initialization parameter bckgrndrate "{}" needs to be non-negative float'.format(bgr)
            if not bgr.isnumeric():
                msgs.append(msg)
            elif float(bgr) < 0.0:
                msgs.append(msg)

        if not validateBool(self.init['trace']):
            msg = 'bckgrndLd initialization parameter trace "{}" needs to be boolean'.format(self.init['trace'])
            msgs.append(msg)
 
        if len(msgs) > 0:
            return False, '\n'.join(msgs)
        

        return True, ""

    def addMsg2MC(self, msgType, mc):
        self.init['msg2mc'][msgType] = mc

    def serializeDict(self):
        if not self.init['bckgrndrate']:
            self.init['bckgrndrate'] = float(self.init['bckgrndrate'])
        self.init['trace'] = cnvrtBool(self.init['trace'])
        return self.init

class ProcessPckt:
    def __init__(self, row):
        self.cmpptn = row[1]
        self.label = row[2]
        self.init = {'timingcode': {}, 
                         'accelname': row[8], 'trace': row[5], 'msg2mc': {}, 'msg2msg': {}, 'groups':[]}

    def addGroup(self, groupName):
        if 'groups' not in self.init:
            self.init['groups'] = []
        if groupName not in self.init['groups']:
            self.init['groups'].append(groupName)
        
    def validate(self):
        # remember this function if it has an interesting timing code dictionary
        if len(self.init['timingcode']) > 0:
            TimingCodeFuncs.append(self)

        if not validateFlag:
            return True, ""

        if self.cmpptn not in cmpPtnInstDict:
            print_err('cp name "{}" in ProcessPckt not recognized'.format(self.cmpptn))
            exit(1)

        msgs = []
        if not validateBool(self.init['trace']):
            msg = 'processPckt initialization trace parameter "{}" needs to be boolean'.format(self.init['trace'])
            msgs.append(msg)

        ok, msg = validateFuncInCP(self.cmpptn, self.label,"processPckt init validation")
        if not ok:
            msgs.append(msg)

        cpi = cmpPtnInstByName[self.cmpptn]
        if cpi is None:
            msg = 'no comp pattern with name "{}" is defined'.format(self.cmpptn)
            msgs.append(msg)
        else:  
            cpfi = cpi.getFuncInst(self.label)
            if cpfi is None:
                msg = 'no function label "{}" in CP'.format(self.label, self.cmpptn)
                msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        for mc in self.init['timingcode']:
            # check if timing code key is the msgType on an input edge
            # to the function being initialized.
            ok, msg = cpfi.msgOnInEdge(mc)
            if not ok:
                msgs.append(msg)
      
        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""


    def addTimingCode(self, mc, tc):
        self.init['timingcode'][mc] = tc

    def addMsg2MC(self, msgType, mc):
        self.init['msg2mc'][msgType] = mc

    def addMsg2sg(self, msgTypeIn, msgTypeOut):
        self.init['msg2msg'][msgTypeIn] = msgTypeOut

    def repTC(self):
        self.init['cmpptn'] = self.cmpptn
        self.init['label'] = self.label
        return self.init

    def serializeDict(self):
        self.init['trace'] = cnvrtBool(self.init['trace'])
        return self.init

class Transfer:
    def __init__(self, row):
        self.cmpptn = row[1]
        self.label = row[2]
        self.init = {'carried': row[3], 
                         'xcp': row[4], 'xlabel': row[5], 'xmsgtype': row[6],
                        'trace': row[7], 'msg2mc': {}, 'groups':[] }

    def addGroup(self, groupName):
        if 'groups' not in self.init:
            self.init['groups'] = []
        if groupName not in self.init['groups']:
            self.init['groups'].append(groupName)
        

    def validate(self):
        if not validateFlag:
            return True, ""

        if self.init['carried'] == "1":
            return True, ""

        if self.cmpptn not in cmpPtnInstDict:
            print_err('cp name "{}" in Transfer init not recognized'.format(self.cmpptn))
            exit(1)

        msgs = []
        if not validateBool(self.init['trace']):
            msg = 'transfer initialization trace parameter "{}" needs to be boolean'.format(self.init['trace'])
            msgs.append(msg)

        if not validateBool(self.init['carried']):
            msg = 'transfer initialization carried parameter "{}" needs to be boolean'.format(self.init['carried'])
            msgs.append(msg)

        ok, msg = validateFuncInCP(self.cmpptn, self.label,"transfer init validation")
        if not ok:
            msgs.append(msg)

        if not cnvrtBool(self.init['carried']) == 1 and self.init['xcp'] not in cmpPtnInstDict:
            msg = 'cp name "{}" in transfer init not recognized'.format(self.init['xcp'])
            return False, msg 

        if not cnvrtBool(self.init['carried']) == 1:
            ok, msg = validateFuncInCP(self.init['xcp'], self.init['xlabel'],"transfer init validation")
            if not ok:
                msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def addMsg2MC(self, msgType, mc):
        self.init['msg2mc'][msgType] = mc

    def serializeDict(self):
        self.init['trace']   = cnvrtBool(self.init['trace'])
        self.init['carried'] = cnvrtBool(self.init['carried'])
        return self.init

def validateCmpPtns():
    global validateFlag

    if not validateFlag:
        return True, ""

    msgs  = []
    for cmpPtnInstName, cpi in cmpPtnInstDict.items():
        valid, msg = cpi.validate()
        if not valid:
            msgs.append(msg)
            
    if len(msgs) > 0:
        return False, '\n'.join(msgs)
    return True, ""


def validateConnections():

    if not validateFlag:
        return True, ""

    msgs = []
    for conn in connectionList:
        valid, msg = conn.validate()
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
   
 
    if v in ('TRUE','True','true','T','t','1', 1):
        return True, ""
    if v in ('FALSE','False','false','F','f','0',0):
        return True, ""
    return False, "error in boolean variable"

def cnvrtBool(v):
    if isinstance(v, str) and v.startswith('@'):
        return v

    if isinstance(v, str) and v.startswith('$'):
        return v

    if isinstance(v, str) and len(v) == 0:
        return 0

    if v in ('TRUE','True','true','T','t','1', 1):
        return 1

    if v in ('FALSE','False','false','F','f','0', 0):
        return 0

    return v

# 
def validateFuncInCP(cmpPtnName, funcName, msg):
    if not validateFlag:
        return True, ""

    if len(cmpPtnName) == 0:
        return False, "unexpected empty cmpPtn name"

    if cmpPtnName not in cmpPtnInstDict:
        msg = '{}: CP "{}" not found in declared comp patterns'.format(msg,cmpPtnName)
        return False, msg  

    cpi = cmpPtnInstDict[cmpPtnName]
    for func in cpi.funcInstList: 
        if func.funcName == funcName:
            return True, "" 

    msg = '{}: func "{}" not found in CP "{}"'.format(msg, funcName, cmpPtnName)
    return False, msg 

def validateFunc(cmpPtnClass, funcName, ):
    if cmpPtnClass in mcodes:
        return True, ""
    return False, 'CmpPtn class "{}" not recognized'.format(cmpPtnClass)


def validateCP(cmpPtnName, msg):
    if not validateFlag:
        return True, ""

    if len(cmpPtnName) == 0:
        return False, "unexpected empty cmpPtn name"

    if cmpPtnName not in cmpPtnInstDict:
        msg = '{}: CP "{}" not found in declared comp patterns'.format(msg,cmpPtnName)
        return False, msg  

    return True, ""

def validateMCInClass(mc, funcClass, msg):
    if not validateFlag:
        return True, ""

    if len(mc) == 0:
        return False, "expected non-empty method code in connection statement"

    if funcClass not in mcodes:
        msg = 'declared function class "{}" not associated with pces'.format(funcClass)
        return False, msg
   
    if mc not in mcodes[funcClass]:
        msg = 'method code "{}" not in pces list of methods for function class "{}"'.format(mc, funcClass)
        return False, msg 

    return True, ""

def cfgStr(initDict):
    cfg = json.dumps(initDict) 
    return cfg

def validateInitializations(initClassDict):
    if not validateFlag:
        return True, ""

    errors = 0

    # go through the cmpPtns and their functions and make sure each is represented
    # in initClassDict
    msgs = []
    for cmpPtnName, cmpPtnInst in cmpPtnInstDict.items():
        if cmpPtnName not in initClassDict:
            msgs.append('comp pattern "{}" has no initializations for its functions'.format(cmpPtnName))
            continue
    
        for func in cmpPtnInst.funcInstList:
            if func.funcName not in initClassDict[cmpPtnName]:
                msgs.append('comp pattern "{}" function "{}" has no initializations for its functions'.format(cmpPtnName, func.funcName))
                continue


    # now validate the initializations we do have
    for cpName, funcInitDict in initClassDict.items():
        for funcName, funcClass in funcInitDict.items():
            # make sure that function has an init line
            valid, msg = funcClass.validate()
            if not valid:
                msgs.append(msg)

    if len(msgs) > 0:
        return False, '\n'.join(msgs)

    return True,""

def directoryAccessible(path):
    try:
        os.access(path, os.R_OK)
    except OSError:
        return False
    else:
        return True

def cleanRow(row):
    rtn = []
    for r in row:
        if r.startswith('#!'):
            r = ''             
        elif len(rtn) > 0 and r.startswith('#'):
            break
        rtn.append(r)

    return rtn

def main():
    global mcodes, validateFlag, initClassDict

    parser = argparse.ArgumentParser()
    parser.add_argument(u'-name', metavar = u'name of system', dest=u'name', required=True)
    parser.add_argument(u'-validate', action='store_true', required=False)

    parser.add_argument(u'-csvDir', metavar = u'directory where csv file is found', dest=u'csvDir', required=True)
    parser.add_argument(u'-yamlDir', metavar = u'directory where yaml are stored', dest=u'yamlDir', required=True)
    parser.add_argument(u'-descDir', metavar = u'directory where auxilary descriptions are stored', 
            dest=u'descDir', required=True)

    # csv input file
    parser.add_argument(u'-csvIn', metavar = u'input csv file name', dest=u'csv_input', required=True)

    # output in the format of cp.yaml
    parser.add_argument(u'-cmpptn', metavar = u'cp file name', dest=u'cmpptn_output', required=True)

    # output in the format of cpInit.yaml
    parser.add_argument(u'-cpInit', metavar = u'cpInit file name', dest=u'cpInit_output', required=True)

    parser.add_argument(u'-cpuOpsDescIn', metavar = u'input operations in the function table for a given cpu Model', dest=u'cpuOpsDesc_input', required=True)

    # method code file is json dictionary whose key is the known function classes
    # and the value is a list of method codes recognized by that class
    parser.add_argument(u'-mc', metavar = u'input method code map file name', dest=u'mc_input', required=True)

    # output of a dictionary whose keys are the comp pattern names, and the value of each
    # is a list of function labels bound to that comp pattern
    parser.add_argument(u'-funcsDescOut', metavar = u'output description of cmpptns and labels', dest=u'funcsDesc_output', required=True)
  
    # output of a list of dictionaries, each identifying a function (by cmp ptn and label) and its timing table.
    # when we do the mapping build we can validate that timing table dictionary
    parser.add_argument(u'-tcDescOut', metavar = u'file name to write description of comp pattern functions that have timing tables',
        dest=u'tcDesc_output', required=True) 

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

    if not args.validate:
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
    #mc_input_file = os.path.join(descDir, args.mc_input)
    exprmnt_input_file = os.path.join(descDir, 'exprmnt.json')
    cpuOpsDesc_input_file = os.path.join(descDir, args.cpuOpsDesc_input)

    cmpptn_output_file = os.path.join(yamlDir, args.cmpptn_output)
    cpInit_output_file = os.path.join(yamlDir, args.cpInit_output)

    funcsDesc_output_file = os.path.join(descDir, args.funcsDesc_output)
    tcDesc_output_file = os.path.join(descDir, args.tcDesc_output)

    sysname = args.name

    errs = 0
    #input_files = (csv_input_file, mc_input_file, cpuOpsDesc_input_file, exprmnt_input_file)
    input_files = (csv_input_file, cpuOpsDesc_input_file, exprmnt_input_file)
    for input_file in input_files:
        if not os.path.isfile(input_file):
            print_err('unable to open input file "{}"'.format(input_file))
            errs += 1
 
    if errs > 0:
        exit(0)

    connections = False
    patterns = False
    initializations = False

    patternsDict = {}
    ptnNameIdx = 0
    ptnTypeIdx = 1
    funcClassIdx = 2
    funcLabelIdx = 3
    srvOpIdx = 4
    srvFuncIdx = 5

    srcCPIdx = 0
    dstCPIdx = 1
    srcLabelIdx = 2
    dstLabelIdx = 3
    msgTypeIdx = 4


    Msg2MCIdx = {}
    Msg2MCIdx['srvReq'] = 5 
    Msg2MCIdx['srvRsp'] = 7
    Msg2MCIdx['measure'] = 6
    Msg2MCIdx['finish'] = 4
    Msg2MCIdx['bckgrndLd'] = 7
    Msg2MCIdx['processPckt'] = 7
    Msg2MCIdx['transfer'] = 8

    Msg2MsgIdx = {}
    Msg2MsgIdx['srvReq'] = 11
    Msg2MsgIdx['processPckt'] = 9
   
    srvRspDirectIdx = 5
    srvRspTCIdx = 3

    GroupsIdx = {}
    GroupsIdx['srvReq'] = 13
    GroupsIdx['srvRsp'] = 9
    GroupsIdx['measure'] = 8
    GroupsIdx['start'] = 10
    GroupsIdx['finish'] = 7
    GroupsIdx['bckgrndld'] = 9
    GroupsIdx['processPckt'] = 11
    GroupsIdx['transfer'] = 10
    GroupsIdx['streamsrc'] = strmSrcIdx['groups']
    GroupsIdx['streamdst'] = strmDstIdx['groups']

    #with open(mc_input_file,'r') as rf:
    #    mcodes = json.load(rf)

    with open(cpuOpsDesc_input_file,'r') as rf:
        cpuOps = json.load(rf)

    with open(exprmnt_input_file, 'r') as rf:
        exprmnts = json.load(rf)

    # gather up the unique operation names
    for _, opList in cpuOps.items():
        for op in opList:
            if not op in allOps:
                allOps.append(op)

    msgs = []
    with open(csv_input_file, newline='') as rf:
        csvrdr = csv.reader(rf)
        lineNum = 0
        for raw in csvrdr:
            row = []
            for v in raw:
                row.append(v.strip())

            if row[0].find('###') > -1:
                if initializations:
                    pieces = row[0].split()
                    className = pieces[1] 
                continue

            row = cleanRow(row)

            if row[0].find('#') > -1:
                continue

            if empty(row):
                continue
            
            if unnamed(row):
                continue

            lineNum += 1

            if row[0].find("Patterns") > -1:
                patterns = True
                maxCols = 6 
                cmpPtnLabel = ''
                cmpPtnName = ''
                cmpPtnType = ''
                funcClass = ''
                funcLabel = ''
                srvOp = ''
                srvFunc = ''
                continue
            
            if row[0].find("Connections") > -1:
                # validate these now so that when reading connections we're assured of
                # binding between cmpPtn and labels
                valid, msg = validateCmpPtns()
                if not valid:
                    print_err(msg)
                    exit(1)
                maxCols = 5

                # validate the cmpPtns
                patterns = False
                connections = True
                srcCP = ''
                dstCP = ''
                srcLabel = ''
                dstLabel = ''
                msgType = ''
                continue

            if row[0].find("Initializations") > -1:
                initializations = True
                maxCols = len(strmSrcIdx)
                patterns = False
                connections = False
                className = ''
                continue

            row = row[:maxCols]
            
            if patterns:
                if len(row[ptnNameIdx]) > 0:
                    cmpPtnName = row[ptnNameIdx]

                if len(row[ptnTypeIdx]) > 0:
                    cmpPtnType = row[ptnTypeIdx]

                funcClass = row[funcClassIdx].strip()
                funcLabel = row[funcLabelIdx].strip()
                srvOp = row[srvOpIdx].strip()
                srvFunc = row[srvFuncIdx].strip()

                # cmpPtn may have a list of functions, we build the class instance only the first time
                if cmpPtnName not in cmpPtnInstDict:
                    cpi = CmpPtnInst(cmpPtnName,cmpPtnType)
                    cmpPtnInstDict[cmpPtnName] = cpi

                # add the function described in the row
                if len(funcLabel) > 0:
                    cmpPtnInstDict[cmpPtnName].addFunc( FuncInst(cmpPtnName, funcClass, funcLabel) )
                if len(srvOp) > 0:
                    cmpPtnInstDict[cmpPtnName].addService(srvOp, srvFunc)

                continue
    
            if connections:
                if len(row[srcCPIdx]) > 0:
                    srcCP = row[srcCPIdx]

                if len(row[dstCPIdx]) > 0:
                    dstCP = row[dstCPIdx]

                if len(row[srcLabelIdx]) > 0:
                    srcLabel = row[srcLabelIdx]
                else:
                    srcLabel = ""

                if len(row[dstLabelIdx]) > 0:
                    dstLabel = row[dstLabelIdx]
                else:
                    dstLabel = ""

                if len(row[msgTypeIdx]) > 0:
                    msgType = row[msgTypeIdx]
                else:
                    msgType = ""

                connectionList.append(Connection(srcCP, dstCP, srcLabel, dstLabel, msgType))
                continue


            if initializations:
                if len(row[0]) > 0 and className != row[0]:
                    # new class. N.B. we otherwise 'coast' maintaining the previous one
                    className = row[0].strip()
              
                row = row[:initRowLen[className]]    

                # notice that an empty cell means that cmpPtnName will be the previous non-empty 
                # entry 
                if len(row[1]) > 0:
                    cmpPtnName = row[1]
                if len(row[2]) > 0:
                    funcLabel = row[2]

                if className == 'srvReq':
                        # save the initialization block in a way we can find it given the 
                        # cmpPtnInst name and the function label
                        if cmpPtnName not in initClassDict:
                           initClassDict[cmpPtnName] = {}

                        if len(row[1]) > 0:
                            # first time creates the class
                            initClassDict[cmpPtnName][funcLabel] = SrvReq(row)
                            
                elif className == 'srvRsp': 
                        if cmpPtnName not in initClassDict:
                           initClassDict[cmpPtnName] = {}

                        # srvRsp carries a map so we treat its initialization differently
                        if len(row[1]) > 0:
                            # first time creates the class
                            initClassDict[cmpPtnName][funcLabel] = SrvRsp(row)

                        if len(row[srvRspTCIdx]) > 0:    
                            tcIdx = srvRspTCIdx
                            # after the first row we'll still have srvRspVar from the previous row 
                            initClassDict[cmpPtnName][funcLabel].addTimingCode(row[tcIdx], row[tcIdx+1])
                      
                        if len(row[srvRspDirectIdx]) > 0: 
                            dpIdx = srvRspDirectIdx
                            initClassDict[cmpPtnName][funcLabel].addDirectPrefix(row[dpIdx])

                elif className == 'processPckt': 
                        if cmpPtnName not in initClassDict:
                           initClassDict[cmpPtnName] = {}

                        if len(row[1]) > 0:
                            initClassDict[cmpPtnName][funcLabel] = ProcessPckt(row)

                        if len(row[3]) > 0:
                            initClassDict[cmpPtnName][funcLabel].addTimingCode(row[3], row[4])

                elif className == 'transfer': 
                        if cmpPtnName not in initClassDict:
                           initClassDict[cmpPtnName] = {}

                        if len(row[1]) > 0:
                            initClassDict[cmpPtnName][funcLabel] = Transfer(row)
                    
                elif className == 'measure': 
                        if cmpPtnName not in initClassDict:
                           initClassDict[cmpPtnName] = {}

                        initClassDict[cmpPtnName][funcLabel] = Measure(row)
                    
                elif className == 'start': 
                        if cmpPtnName not in initClassDict:
                           initClassDict[cmpPtnName] = {}
                        initClassDict[cmpPtnName][funcLabel] = Start(row)

                elif className == 'finish': 
                        if cmpPtnName not in initClassDict:
                           initClassDict[cmpPtnName] = {}
                        initClassDict[cmpPtnName][funcLabel] = Finish(row)

                elif className == 'streamsrc':
                        if cmpPtnName not in initClassDict:
                           initClassDict[cmpPtnName] = {}
                        initClassDict[cmpPtnName][funcLabel] = StreamSrc(row)

                elif className == 'streamdst':
                        if cmpPtnName not in initClassDict:
                           initClassDict[cmpPtnName] = {}
                        initClassDict[cmpPtnName][funcLabel] = StreamDst(row)

                if className in Msg2MCIdx:
                    ridx = Msg2MCIdx[className]      
                    if len(row[ridx]) > 0:
                        initClassDict[cmpPtnName][funcLabel].addMsg2MC(row[ridx], row[ridx+1])

                if className in Msg2MsgIdx:
                    ridx = Msg2MsgIdx[className]
                    if len(row[ridx]) > 0:
                        initClassDict[cmpPtnName][funcLabel].addMsg2Msg(row[ridx], row[ridx+1])

                if className in GroupsIdx:
                    ridx = GroupsIdx[className]
                    if ridx <= len(row)-1 and len(row[ridx]) > 0: 
                        initClassDict[cmpPtnName][funcLabel].addGroup(row[ridx])
                continue

    valid, msg = validateConnections()
    if not valid:
        print_err(msg)
        exit(1)

    # validate initialization data
    valid, msg = validateInitializations(initClassDict)
    if not valid:
        msgs = msg.split('\n')
        for msg in msgs:
            print_err(msg)
        exit(1)

    valid, msg = validateCmpPtns()
    if not valid:
        msgs = msg.split('\n')
        for msg in msgs:
            print_err(msg)
        exit(1)

    patternsDict = {}
    for cmpPtnInstName, cmpPtnInst in cmpPtnInstDict.items():
        patternsDict[cmpPtnInstName] = cmpPtnInst.repDict()
 
    rtn = {'patterns': patternsDict}
    with open(cmpptn_output_file, 'w') as wf:
        yaml.dump(rtn, wf)

    # create cpInit
    cpInitDict = {'dictname': sysname, 'initlist': {}}

    # initClassDict[ cmp ptn name ][func label in cmp ptn] is the init 
    # for the class associated with that func
    for cpName, funcInitDict in initClassDict.items():

        # cpInitDict[ cpName ] is an initDict
#FINDME need to distinguish between name and type
        initDict = {'name': cpName, 'cptype': cpName, 'useyaml': True, 'cfg': {}, 'msgs':[]}

        if cpName in messages:
            for msgType in messages[cpName]:
                msgDict = {'msgtype': msgType, 'ispckt': True}
                initDict['msgs'].append(msgDict)

        # for each function in funcInitDict create an initialization string
        for instFunc in funcInitDict:
            initDict['cfg'][instFunc] = cfgStr(funcInitDict[instFunc].serializeDict())
        cpInitDict['initlist'][cpName] = initDict  


    with open(cpInit_output_file, 'w') as wf:
        yaml.dump(cpInitDict, wf, default_flow_style=False)

    funcsDict = {}
    funcTimingCodesList = []
    for cmpptn, cmpptnInst in cmpPtnInstByName.items():
        funcsDict[cmpptn] = cmpptnInst.repFuncs()
         
    with open(funcsDesc_output_file, 'w') as wf:
        json.dump(funcsDict, wf)

    timingCodeList = []
    for funcInst in TimingCodeFuncs:
        timingCodeList.append( funcInst.repTC())

    with open(tcDesc_output_file, 'w') as wf:
        json.dump(timingCodeList, wf)

if __name__ == '__main__':
    main()

