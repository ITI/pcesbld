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
wiredConnList = []
wirelessConnList = []

switchNames = {}
routerNames = {}
endptNames = {}
networkNames = {}
devNames = {}

devDesc = []

netNameIdx = 0
netScaleIdx = 1
netMediaIdx = 2
netSwitchIdx = 3
netEndptIdx = 4
netRouterIdx = 5
netGroupIdx = 6

devNameIdx = 0
devModelIdx = 1
devGroupIdx = 2
devPeerIdx = 3
devFacesIdx = 4
devSimpleIdx  = 5

endptNameIdx = 0
endptModelIdx = 1
endptCoreIdx = 2
endptGroupIdx = 3
endptAccelNameIdx = 4
endptAccelModelIdx = 5
endptPeerIdx = 6
endptNetworkIdx = 7

networks = False
switches = False
routers  = False
endpoints = False
connections = False

modelDict = {}

class Network:
    def __init__(self, row): 
        self.name = row[netNameIdx]
        self.netscale = row[netScaleIdx]
        self.mediatype = row[netMediaIdx]
        self.switches = []
        self.routers = []
        self.endpts  = []
        self.groups = []
        networkNames[self.name] = self

    def addSwitch(self, switchName):
        if switchName not in self.switches:
            self.switches.append(switchName)

    def addEndpt(self, endptName):
        if endptName not in self.endpts:
            self.endpts.append(endptName)

    def addRouter(self, routerName):
        if routerName not in self.routers:
            self.routers.append(routerName)

    def addGroup(self, groupName):
        if groupName not in self.groups:
            self.groups.append(groupName)

    def validate(self):
        msgs = []
        if self.netscale not in ('LAN','WAN','T3','T2','T1'):
            msg = "network {} netscale '{}' not found in expected list".format(self.name, self.netscale)
            msgs.append(msg)

        if self.mediatype not in ('wired','wireless'):
            msg = "network {} mediatype '{}' not found in expected list".format(self.name, self.mediatype)
            msgs.append(msg)

        for swtch in self.switches:
            if swtch not in switchNames:
                msg = 'network {} includes switch {} with no definition'.format(self.name, swtch)
                msgs.append(msg)

        for router in self.routers:
            if router not in routerNames:
                msg = 'network {} includes router {} with no definition'.format(self.name, router)
                msgs.append(msg)

        for endpt in self.endpts:
            if endpt not in endptNames:
                msg = 'network {} includes endpoint {} with no definition'.format(self.name, endpt)
                msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def repDict(self):
        rd = {'name': self.name, 'groups': self.groups, 'netscale': self.netscale, 'mediatype': self.mediatype,
              'endpts': self.endpts, 'switches': self.switches, 'routers': self.routers}
        return rd

    def attrbDict(self):
        rad = {'name': self.name, 'groups': self.groups, 'media': self.mediatype, 'scale': self.netscale}
        return rad

class Switch:
    def __init__(self, row): 
        self.name = row[devNameIdx]
        self.model = row[devModelIdx]
        if len(row[devSimpleIdx]) == 0:
            self.simple = 'TRUE'
        else:
            self.simple = row[devSimpleIdx]
        self.groups = []
        self.peers = []
        self.faces = []
        self.intrfcs = []
        self.netRef = {}

        switchNames[self.name] = self 
        devNames[self.name] = self

    def addGroup(self, groupName):
        if groupName not in self.groups:
            self.groups.append(groupName)

    def addPeer(self, peerName):
        if peerName not in self.peers:
            self.peers.append(peerName)

    def addNetwork(self, netName):
        if netName not in self.faces:
            self.faces.append(netName)

    def addIntrfc(self, intrfcDict):
        self.intrfcs.append(intrfcDict)

    def validate(self):
        msgs = []
        if len(self.model) == 0:
            msg = 'switch {} lacks model description'.format(self.name)
            msgs.append(msg)

        valid, boolmsg = validateBool(self.simple)
        if not valid:
    
            msg = "switch {} 'simple' flag is not boolean".format(self.name, self.model)
            msgs.append(msg) 
        else:
            self.simple = cnvrtBool(self.simple)
  
        if len(modelDict) > 0 and len(self.model) > 0 and self.model  not in modelDict['Switch']:
            msg = 'switch {} model {} not recognized from timing file'.format(self.name, self.model)
            msgs.append(msg)



        for peer in self.peers:
            if not validDev(peer):
                msg = 'switch {} declares unrecognized peer {}'.format(self.name, peer)
                msgs.append(msg)

        for net in self.faces:
            if net not in networkNames:
                msg = 'switch {} declares facing unknown network {}'.format(self.name, net)
                msgs.append(msg)
        
        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def repDict(self):
        rd = {'name': self.name, 'groups': self.groups, 'model': self.model, 'simple': 1, 'interfaces': self.intrfcs}
        return rd

    def attrbDict(self):
        rad = {'name': self.name, 'groups': self.groups, 'model': self.model}
        return rad

class Router:
    def __init__(self, row): 
        self.name = row[devNameIdx]
        self.model = row[devModelIdx]
        self.simple = row[devSimpleIdx]
        self.groups = []
        self.peers = []
        self.faces = []
        self.intrfcs = []
        self.netRef = {}

        routerNames[self.name] = self
        devNames[self.name] = self

    def addGroup(self, groupName):
        if groupName not in self.groups:
            self.groups.append(groupName)

    def addPeer(self, peerName):
        if peerName not in self.peers:
            self.peers.append(peerName)

    def addNetwork(self, netName):
        if netName not in self.faces:
            self.faces.append(netName)

    def addIntrfc(self, intrfcDict):
        self.intrfcs.append(intrfcDict)

    def validate(self):
        msgs = []
        if len(self.model) == 0:
            msg = 'router {} lacks model description'.format(self.name)
            msgs.append(msg)

        if len(modelDict) > 0 and len(self.model) > 0 and self.model not in modelDict['Router']:
            msg = 'router {} model {} not recognized from devDesc file'.format(self.name, self.model)

        for peer in self.peers:
            if not validDev(peer):
                msg = 'router {} declares unrecognized peer {}'.format(self.name, peer)
                msgs.append(msg)

        for net in self.faces:
            if net not in networkNames:
                msg = 'router {} declares facing unknown network {}'.format(self.name, net)
                msgs.append(msg)
        
        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def repDict(self):
        rd = {'name': self.name, 'groups': self.groups, 'model': self.model, 
            'simple': self.simple, 'interfaces': self.intrfcs}
        return rd

    def attrbDict(self):
        rad = {'name': self.name, 'groups': self.groups, 'model': self.model}
        return rad

class Endpt:
    def __init__(self, row): 
        self.name = row[devNameIdx]
        self.model = row[devModelIdx]
        self.cores = row[endptCoreIdx]
        self.accel = {}
        self.groups = []
        self.peers = []
        self.faces = []
        self.intrfcs = []
        self.netRef = {}

        endptNames[self.name] = self
        devNames[self.name] = self

    def addGroup(self, groupName):
        if groupName not in self.groups:
            self.groups.append(groupName)

    def addPeer(self, peerName):
        if peerName not in self.peers:
            self.peers.append(peerName)

    def addNetwork(self, netName):
        if netName not in self.faces:
            self.faces.append(netName)

    def addAccel(self, accelName, accelModel):
        if accelName not in self.accel:
            self.accel[accelName] = accelModel

    def addIntrfc(self, intrfcDict):
        self.intrfcs.append(intrfcDict)


    def validate(self):
        msgs = []
        if len(self.model) == 0:
            msg = 'endpoint {} lacks model description'.format(self.name)
            msgs.append(msg)

        if len(self.cores)==0:
            self.cores = 1
        elif not self.cores.isdigit() or int(self.cores) < 1:
            msg = 'endpoint {} number of cores {} not positive integer'.format(self.name, self.cores)
            msgs.append(msg)
        else:
            self.cores = int(self.cores)

        if len(modelDict) > 0 and len(self.model) > 0 and self.model not in modelDict['CPU']:
            msg = 'endpoint {} model {} not recognized from devDesc file'.format(self.name, self.model)

        for peer in self.peers:
            if not validDev(peer):
                msg = 'endpoint {} declares unrecognized peer {}'.format(self.name, peer)
                msgs.append(msg)

        for net in self.faces:
            if net not in networkNames:
                msg = 'endpoint {} declares facing unknown network {}'.format(self.name, net)
                msgs.append(msg)
        
        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def repDict(self):
        rd = {'name': self.name, 'groups': self.groups, 'model': self.model, 'cores': self.cores, \
                'accel': self.accel, 'interfaces': self.intrfcs}
        return rd

    def repDesc(self):
        rd = {'name': self.name, 'model': self.model, 'cores': self.cores, 'accel': self.accel}
        return rd

    def attrbDict(self):
        rad = {'name': self.name, 'groups': self.groups, 'model': self.model}
        return rad

class WirelessConnection:
    def __init__(self, row):
        self.dev = row[0]
        self.network = row[1]
        self.mediatype = "wireless"

    def validate(self):
        msgs = []
        if not validDev(self.dev):
            msg = "wireless connection specifices device {} which is not defined".format(self.dev)
            msgs.append(msg)

        if self.network not in networkNames:
            msg = 'wireless connection from {} specifies facing unknown network {}'.format(self.dev, self.network)
            msgs.append(msg)
   
        if self.mediatype not in ('wired', 'wireless'):
            msg = 'wireless connection from {} specifies unknown network media type {}'.format(self.dev, self.mediatype)
            msgs.append(msg)
        
        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def createIntrfc(self):
        intrfc = {}
        intrfc['name'] = 'intrfc@'+self.dev+'->'+self.network
        intrfc['groups'] = []
        intrfc['device'] = self.dev
        intrfc['carry'] = []
        intrfc['wireless'] = []
        intrfc['cable'] = ""
        intrfc['faces'] = self.network
        intrfc['devname'] = self.dev

        if self.dev1 in switchNames:
            intrfc['devtype'] = 'Switch'
        elif self.dev1 in routerNames:
            intrfc['devtype'] = 'Router'
        elif self.dev1 in endptNames:
            intrfc['devtype'] = 'Endpt'

        intrfc['mediatype'] = self.mediatype
        intrfcList.append(intrfc)
        return intrfc

def IntrfcAttrb(intrfc):
    ia = {'name':intrfc['name'], 'groups': intrfc['groups'], 'devtype': intrfc['devtype'], 'devname': intrfc['devname'], 'media': intrfc['mediatype'], 'faces': intrfc['faces']}
    return ia

class WiredConnection:
    def __init__(self, row):
        self.dev1 = row[0]
        self.dev2 = row[1]
        self.cable = row[2]

    def createIntrfcs(self):
        intrfc1 = {}
        intrfc1['name'] = 'intrfc@'+self.dev1+'-'+self.dev2
        intrfc1['groups'] = []
        intrfc1['device'] = self.dev1
        intrfc1['carry'] = []
        intrfc1['wireless'] = []
        intrfc1['devname'] = self.dev1

        if self.dev1 in switchNames:
            intrfc1['devtype'] = 'Switch'
        elif self.dev1 in routerNames:
            intrfc1['devtype'] = 'Router'
        elif self.dev1 in endptNames:
            intrfc1['devtype'] = 'Endpt'

        # figure out which network contains both of these devices
        shared, sharedNets = sharedNetwork(self.dev1, self.dev2)
        if not shared:
            msg = 'closed connection ({},{}) endpoints do not share a network'.format(self.dev1, self.dev2)
            msgs.append(msg)
        else:
            intrfc1['faces'] = sharedNets[0]
            # media type is the type of the network the interface faces
            net = networkNames[sharedNets[0]]
            intrfc1['mediatype'] = net.mediatype 


        intrfc2 = {}
        intrfc2['name'] = 'intrfc@'+self.dev2+'-'+self.dev1
        intrfc2['groups'] = []
        intrfc2['device'] = self.dev2
        intrfc2['carry'] = []
        intrfc2['wireless'] = []
        intrfc2['devname'] = self.dev2

        if self.dev2 in switchNames:
            intrfc2['devtype'] = 'Switch'
        elif self.dev2 in routerNames:
            intrfc2['devtype'] = 'Router'
        elif self.dev2 in endptNames:
            intrfc2['devtype'] = 'Endpt'

        intrfc2['faces'] = intrfc1['faces']
        if 'mediatype' in intrfc1:
            intrfc2['mediatype'] = intrfc1['mediatype']

        if intrfc1['devtype'] == 'Switch':
                dev = switchNames[self.dev1]
                dev.addIntrfc(intrfc1)

        if intrfc1['devtype'] == 'Router':
                dev = routerNames[self.dev1]
                dev.addIntrfc(intrfc1)

        if intrfc1['devtype'] == 'Endpt':
                dev = endptNames[self.dev1]
                dev.addIntrfc(intrfc1)

        
        if intrfc2['devtype'] == 'Switch':
                dev = switchNames[self.dev2]
                dev.addIntrfc(intrfc2)

        elif intrfc2['devtype'] == 'Router':
                dev = routerNames[self.dev2]
                dev.addIntrfc(intrfc2)

        elif intrfc2['devtype'] == 'Endpt':
                dev = endptNames[self.dev2]
                dev.addIntrfc(intrfc2)

        if self.cable == 1 or self.cable == "1" :
            intrfc1['cable'] = intrfc2['name']
            intrfc2['cable'] = intrfc1['name']

        intrfcList.append(intrfc1)
        intrfcList.append(intrfc2)

    def validate(self):
        msgs = []
        if not validDev(self.dev1):
            msg = "connection specifices device {} which is not defined".format(self.dev1)
            msgs.append(msg)

        if not validDev(self.dev2):
            msg = "connection specifices device {} which is not defined".format(self.dev2)
            msgs.append(msg)

        # check that the devices are included in the same network
        shared, _ = sharedNetwork(self.dev1, self.dev2)
        if not shared:
            msg = 'connection ({},{}) endpoints do not share a network'.format(self.dev1, self.dev2)
            msgs.append(msg)

        valid, boolmsg = validateBool(self.cable)
        if not valid:
             msg = 'connection ({},{}) has non-Boolean cable entry'.format(self.dev1, self.dev2)
             msgs.append(msg)
        else:
            self.cable = cnvrtBool(self.cable)

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

def print_err(*a) : 
    print(*a, file=sys.stderr)


# called
def validateBool(v):
    if v in ('TRUE','True','true','T','t','1'):
        return True, ""
    if v in ('FALSE','False','false','F','f','0'):
        return True, ""
    return False, "error in boolean variable"

def cnvrtBool(v):
    if v in ('TRUE','True','true','T','t','1'):
        return 1
    if v in ('FALSE','False','false','F','f','0'):
        return 0
    print_err("string {} is not a bool".format(v))
    return None

def validDev(devName):
    return devName in switchNames or devName in routerNames or devName in endptNames

def validateNetworks():
    # check that all networks have unique names
    netnames = {}
    msgs = []
    for net in networkList:
        if net.name in netnames:
            msg = 'network name {} duplicated'.format(net.name)
            msgs.append(msg)
        netnames[net.name] = True

        valid, msg = net.validate()
        if not valid:
            msgs.append(msg)

    if len(msgs) > 0:
        return False, '\n'.join(msgs)

    return True, ""


def validateSwitches():
    # check that all switches have unique names
    switchnames = {}
    msgs = []
    for swtch in switchList:
        if swtch.name in switchnames:
            msg = 'switch name {} duplicated'.format(swtch.name)
            msgs.append(msg)

        switchnames[swtch.name] = True 

        valid, msg = swtch.validate()
        if not valid:
            msgs.append(msg)

    if len(msgs) > 0:
        return False, '\n'.join(msgs)

    return True, ""

def validateRouters():
    # check that all routers have unique names
    routernames = {}
    msgs = []
    for rtr in routerList:
        if rtr.name in routernames:
            msg = 'router name {} duplicated'.format(rtr.name)
            msgs.append(msg)
        routernames[rtr.name] = True 

        valid, msg = rtr.validate()
        if not valid:
            msgs.append(msg)

    if len(msgs) > 0:
        return False, '\n'.join(msgs)

    return True, ""

def validateEndpts():
    # check that all endpts have unique names
    endptnames = {}
    msgs = []
    for endpt in endptList:
        if endpt.name in endptnames:
            msg = 'endpt name {} duplicated'.format(endpt.name)
            msgs.append(msg)

        endptnames[endpt.name] = True 

        valid, msg = endpt.validate()
        if not valid:
            msgs.append(msg)

    if len(msgs) > 0:
        return False, '\n'.join(msgs)

    return True, ""

def validateConnections():
    # check that all connections are unique in naming endpoints.
    # connections assumed to be symmetric
    #
    msgs = []
    pairs = {}

    for conn in wirelessConnList:
        valid, msg = conn.validate()
        if not valid:
            msgs.append(msg)

    for conn in wiredConnList:
        pair = (conn.dev1, conn.dev2)
        if pair in pairs:
            msg = 'connection ({}, {}) is replicated'.format(dev1, dev2)
            msgs.append(msg)
        revpair = (conn.dev2, conn.dev1)
        if pair==revpair:
            msg = 'only one of connection ({},{}) and ({},{}) allowed'.format(dev1,dev2,dev2,dev1)
            msgs.append(msg)
        
        valid, msg = conn.validate()
        if not valid:
            msgs.append(msg)

    for swtch, swtchInst in switchNames.items():
        for peer in swtchInst.peers:
            shared, _ = sharedNetwork(swtch, peer)
            if not shared:
                msg = 'switch {} does not share network with peer {}'.format(swtch, peer)
                msgs.append(msg)

    for rtr, rtrInst in routerNames.items():
        for peer in rtrInst.peers:
            shared, _ = sharedNetwork(rtr, peer)
            if not shared:
                msg = 'router {} does not share network with peer {}'.format(rtr, peer)
                msgs.append(msg)

    for endpt, endptInst in endptNames.items():
        for peer in endptInst.peers:
            shared, _ = sharedNetwork(endpt, peer)
            if not shared:
                msg = 'endpt {} does not share network with peer {}'.format(endpt, peer)
                msgs.append(msg)

    if len(msgs) > 0:
        return False, '\n'.join(msgs)

    return True, ""


def validateNames():
    msgs = []
    for net in networkNames:
        if net in switchNames or net in routerNames or net in endptNames:
            msg = 'network name {} duplicated in devices'.format(net)
            msgs.append(msg)

    for swtch in switchNames:
        if swtch in routerNames or swtch in endptNames:
            msg = 'switch name {} duplicated in devices'.format(swtch)
            msgs.append(msg)

    for router in routerNames:
        if router in endptNames:
            msg = 'router name {} duplicated in devices'.format(router)
            msgs.append(msg)

    if len(msgs) > 0:
        return False, '\n'.join(msgs)

    return True, ""

def sharedNetwork(dev1, dev2):
    shared = []
    dev1Inst = devNames[dev1]
    dev2Inst = devNames[dev2]
    
    for net1 in dev1Inst.netRef:
        for net2 in dev2Inst.netRef:
            if net1==net2:
                shared.append(net1)
                
    return len(shared) > 0, shared


def discoverRefNetworks():
    # tag the endpoints listed for a network as referencing it
    for net in networkList:
        for endpt in net.endpts:
            endptNames[endpt].netRef[net.name] = True

        for swtch in net.switches:
            switchNames[swtch].netRef[net.name] = True

        for router in net.routers:
            routerNames[router].netRef[net.name] = True


# for now create wireless links, think about what to do with wired links
# in wireless interfeaces
def createLinks():
    for net in networkList:
        for endpt in net.endpts:
            # look at each of the endpt interfaces for an wireless interface
            endptInst = devNames[endpt]
            for intrfc in endptInst.intrfcs:
                if intrfc['mediatype'] == 'wireless':
                     for peer in net.endpts:
                        if peer==endpt:
                            continue
                        peerInst = devNames[peer]

                        for peerIntrfc in peerInst.intrfcs:
                            if not peerIntrfc['mediatype'] == 'wireless':
                                continue
                            # pair these up once
                            if peerIntrfc['name'] < intrfc['name']:
                                continue
                             
                            intrfc['wireless'].append(peerIntrfc['name']) 
                            peerIntrfc['wireless'].append(intrfc['name']) 
                        
def wiredoryAccessible(path):
    """
    Checks if a wiredory is accessible.

    Args:
        path: The path to the wiredory.

    Returns:
        True if the wiredory is accessible, False otherwise.
    """
    try:
        os.access(path, os.R_OK)
    except OSError:
        return False
    else:
        return True
 
 
def main():
    global endptList, networkList, switchList, routerList, wiredConnList

    parser = argparse.ArgumentParser()
    parser.add_argument(u'-name', metavar = u'name of system', dest=u'name', required=True)
    parser.add_argument(u'-validate', action='store_true', required=False)
    parser.add_argument(u'-csvDir', metavar = u'wiredory where csv file is found', dest=u'csvDir', required=True)
    parser.add_argument(u'-yamlDir', metavar = u'wiredory where results are stored', dest=u'yamlDir', required=True)
    parser.add_argument(u'-descDir', metavar = u'wiredory where auxilary descriptions are stored', 
            dest=u'descDir', required=True)

    # csv input file
    parser.add_argument(u'-csvIn', metavar = u'input csv file name', dest=u'csv_input', required=True)

    # input file, json, map of cpu, switch, router, and accelerator models extracted
    # from execution timing tables, dictionary key is device type, value is list of models known
    # for that device type
    parser.add_argument(u'-modelDescIn', metavar = u'input file of models of computation devices', dest=u'modelDescIn', required=True)

    # results file in the format of topo.yaml
    parser.add_argument(u'-topoOut', metavar = u'output topo file name', dest=u'topo_results', required=True)

    # description file, json, of list of cpu descriptions : topo name, model, cores, accel  dict
    parser.add_argument(u'-cpuDescOut', metavar = u'output file of cpu description', dest=u'cpuDescOut', required=True)

    # description file, json, of list of object names and groups
    parser.add_argument(u'-attrbDescOut', metavar = u'file of object attribue descriptions', dest=u'attrbDescOut', required=True)

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

    topoName  = args.name
    csvDir = args.csvDir
    yamlDir = args.yamlDir
    descDir = args.descDir

    # make sure we have access to these wiredories
    test_dirs = (csvDir, yamlDir, descDir)

    errs = []
    for tdir in test_dirs:
        if not os.path.isdir(tdir):
            errs.append('wiredory {} does not exist'.format(tdir))
        elif not wiredoryAccessible(tdir):
            errs.append('wiredory {} is not accessible'.format(tdir))

    if len(errs) > 0:
        for msg in errs:
            print(msg)
        exit(1)        

    csv_input_file = os.path.join(csvDir, args.csv_input)
    topo_results_file = os.path.join(yamlDir, args.topo_results)
    modelDescIn_file = os.path.join(descDir, args.modelDescIn)
    cpuDescOut_file   = os.path.join(descDir, args.cpuDescOut)
    attrbDescOut_file = os.path.join(descDir, args.attrbDescOut)

    # test the input files
    test_inputs = (csv_input_file, modelDescIn_file)

    for file in test_inputs:
        if not os.path.isfile(file):
            errs.append('input file {} does not exist'.format(file))
    if len(errs) > 0:
        for msg in errs:
            print(msg)
        exit(1)        

    # get the models description
    with open(modelDescIn_file, 'r') as rf:
        modelDict = json.load(rf)

    networks = False
    switches = False
    routers  = False
    endpoints = False
    connections = False
    
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
            rowTypes = ('Networks', 'Switches', 'Routers', 'Endpoints', 'Wired-Connections', 'Wireless-Connections')
            for rowtype in rowTypes:
                if row[0].find(rowtype) > -1:
                    matchCode = rowtype 

           
            if matchCode == "Networks": 
                    networks = True
                    switches = False
                    routers  = False
                    endpoints = False
                    wiredConn = False
                    wirelessConn = False
                    continue

            elif matchCode == "Switches": 
                    networks = False
                    switches = True
                    routers  = False
                    endpoints = False
                    wiredConn = False
                    wirelessConn = False
                    continue

            elif matchCode == "Routers": 
                    networks = False
                    switches = False
                    routers  = True
                    endpoints = False
                    wiredConn = False
                    wirelessConn = False
                    continue

            elif matchCode == "Endpoints": 
                    networks = False
                    switches = False
                    routers  = False
                    endpoints = True
                    wiredConn = False
                    wirelessConn = False
                    continue

            elif matchCode == "Wired-Connections": 
                    networks = False
                    switches = False
                    routers  = False
                    endpoints = False
                    wiredConn = True
                    wirelessConn = False
                    continue

            elif matchCode == "Wireless-Connections": 
                    networks = False
                    switches = False
                    routers  = False
                    endpoints = False
                    wiredConn = False
                    wirelessConn = True
                    continue

            if networks:
                if len(row[netSwitchIdx]) > 0:
                    swtch = row[netSwitchIdx]

                if len(row[netEndptIdx]) > 0:
                    endpt = row[netEndptIdx]

                if len(row[netRouterIdx]) > 0:
                    router = row[netRouterIdx]

                if len(row[netGroupIdx]) > 0:
                    group = row[netGroupIdx]

                # if the first line of the network create
                # an instance of the network class
                if len(row[netNameIdx]) > 0:
                    networkList.append(Network(row))

                if len(row[netSwitchIdx]) > 0:
                    networkList[-1].addSwitch(swtch)
                    swtch = ''

                if len(row[netRouterIdx]) > 0:
                    networkList[-1].addRouter(router)
                    router = '' 

                if len(row[netEndptIdx]) > 0:
                    networkList[-1].addEndpt(endpt)
                    endpt = ''

                if len(row[netGroupIdx]) > 0:
                    networkList[-1].addGroup(group)
                    group = ''

                if len(row[netGroupIdx]) > 0:
                    networkList[-1].addGroup(group)
                    group = ''

                continue

            if switches:
                if len(row[devGroupIdx]) > 0:
                    group = row[devGroupIdx]
                
                if len(row[devPeerIdx]) > 0:
                    peer = row[devPeerIdx]
                
                if len(row[devFacesIdx]) > 0:
                    net = row[devFacesIdx]
                
                if len(row[devNameIdx]) > 0:
                    switchList.append(Switch(row))
            
                if len(row[devGroupIdx]) > 0:
                    switchList[-1].addGroup(group)
                    group = ''

                if len(row[devPeerIdx]) > 0:
                    switchList[-1].addPeer(peer)
                    peer = ''

                if len(row[devFacesIdx]) > 0:
                    switchList[-1].addNetwork(net)
                    group = ''

                continue

            if routers:
                if len(row[devGroupIdx]) > 0:
                    group = row[devGroupIdx]
                
                if len(row[devPeerIdx]) > 0:
                    peer = row[devPeerIdx]
                
                if len(row[devFacesIdx]) > 0:
                    net = row[devFacesIdx]
                
                if len(row[devNameIdx]) > 0:
                    routerList.append(Router(row))

                if len(row[devGroupIdx]) > 0:
                    routerList[-1].addGroup(group)
                    group = ''

                if len(row[devPeerIdx]) > 0:
                    routerList[-1].addPeer(peer)
                    peer = ''

                if len(row[devFacesIdx]) > 0:
                    routerList[-1].addNetwork(net)
                    net = ''

                continue

            if endpoints:
                if len(row[endptGroupIdx]) > 0:
                    group = row[endptGroupIdx]
                
                if len(row[endptPeerIdx]) > 0:
                    peer = row[endptPeerIdx]
                
                if len(row[endptNetworkIdx]) > 0:
                    net = row[endptNetworkIdx]
                
                if len(row[endptAccelNameIdx]) > 0:
                    accelname = row[endptAccelNameIdx]
                
                if len(row[endptAccelModelIdx]) > 0:
                    accelmodel = row[endptAccelModelIdx]
                
                if len(row[endptNameIdx]) > 0:
                    endptList.append(Endpt(row))

                if len(row[endptGroupIdx]) > 0:
                    endptList[-1].addGroup(group)
                    group = ''

                if len(row[endptPeerIdx]) > 0:
                    endptList[-1].addPeer(peer)
                    peer = ''

                if len(row[endptNetworkIdx]) > 0:
                    endptList[-1].addNetwork(net)
                    net = ''

                if len(row[endptAccelNameIdx]) > 0:
                    endptList[-1].addAccel(accelname, accelmodel)
                    accel = ''

                continue

            if wiredConn:
                wiredConnList.append(WiredConnection(row))
            continue

            if wirelessConn:
                wirelessConnList.append(WirelessConnection(row))
            continue

    msgs = []
    valid, msg = validateNetworks()
    if not valid:
        msgs.append(msg)

    valid, msg = validateSwitches()
    if not valid:
        msgs.append(msg)

    valid, msg = validateRouters()
    if not valid:
        msgs.append(msg)

    valid, msg = validateEndpts()
    if not valid:
        msgs.append(msg)

    discoverRefNetworks() 

    valid, msg = validateConnections()
    if not valid:
        msgs.append(msg)

    valid, msg = validateNames()
    if not valid:
        msgs.append(msg)

    if len(msgs) > 0:
        for msg in msgs:
            msg.replace('\n','')
            print_err(msg)
        exit(1)

    # create interfaces for wired connections
    for conn in wiredConnList:
        conn.createIntrfcs()

    # create interfaces for wireless connections
    for conn in wirelessConnList:
        conn.createIntrfcs()

    # include implied links
    createLinks()

    # come back for more interfaces, dealing with wireless, etc

    rtn = {'networks': [], 'routers': [], 'switches': [], 'endpts': [], 'name': topoName}

    for netDict in networkList:
        rtn['networks'].append(netDict.repDict())

    for rtrDict in routerList:
        rtn['routers'].append(rtrDict.repDict())

    for swtchDict in switchList:
        rtn['switches'].append(swtchDict.repDict())

    for endptDict in endptList:
        rtn['endpts'].append(endptDict.repDict())

    with open(topo_results_file, 'w') as wf:
        yaml.dump(rtn, wf)

    desc = []
    for endpt in endptList:
        desc.append(endpt.repDesc())

    with open(cpuDescOut_file, 'w') as wf:
        json.dump(desc, wf)

    # create the objAttrib dictionary
    ad = {'Network': [], 'Switch': [], 'Router' :[], 'Endpoint': [], 'Interface' :[]}
    for net in networkList:
        ad['Network'].append(net.attrbDict()) 

    for switch in switchList:
        ad['Switch'].append(switch.attrbDict()) 

    for router in routerList:
        ad['Switch'].append(router.attrbDict()) 

    for endpt in endptList:
        ad['Switch'].append(endpt.attrbDict())

    for intrfc in intrfcList:
        ad['Interface'].append(IntrfcAttrb(intrfc)) 

    with open(attrbDescOut_file, 'w') as wf:
        json.dump(ad, wf)

if __name__ == '__main__':
    main()

