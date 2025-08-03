import csv
import pdb
import yaml
import json
import sys
import os
import argparse
import ipaddress

# Globals
validateFlag = False

devNameIdx = 0
devNetIdx = 1
devIntIPIdx = 2
devExtIPIdx = 3

netNameIdx = 0
netIntCIDRIdx = 1
netExtCIDRIdx = 2

feedNameIdx = 0
feedActiveIdx = 1
feedSrcTypeIdx = 2
feedSrcSpecIdx = 3
feedTimeIdx = 4
feedDilationIdx = 5
feedStartIdx = 6

endpoints = False
networks = False

netList = []
deviceList = []
feedList = []
networkDevices = {}

netMap = {}

def print_err(*a) : 
    print(*a, file=sys.stderr)

def is_valid_cidr(cidr_string):
    """
    Checks if a string is a legitimate CIDR representation of an IP network.

    Args:
        cidr_string (str): The string to validate.

    Returns:
        bool: True if the string is a valid CIDR, False otherwise.
    """
    try:
        # Attempt to create an IPv4Network or IPv6Network object
        # from the given string. If it's not a valid CIDR,
        # an exception will be raised.
        ipaddress.ip_network(cidr_string)
        return True
    except ValueError:
        # A ValueError indicates that the string is not a valid
        # IP address or network in CIDR format.
        return False

def is_ip_in_cidr(ip_address_str, cidr_network_str):
  """
  Tests whether a string representing an IP address is within a given CIDR network.

  Args:
    ip_address_str: A string representing the IP address (e.g., "192.168.1.5").
    cidr_network_str: A string representing the CIDR network (e.g., "192.168.1.0/24").

  Returns:
    True if the IP address is within the CIDR network, False otherwise.
  """
  try:
    ip_address = ipaddress.ip_address(ip_address_str)
    network = ipaddress.ip_network(cidr_network_str, strict=False) # strict=False allows host bits to be set in network address
    return ip_address in network
  except ValueError as e:
    return False


def is_legal_ip_address(ip_string):
  """
  Tests if a string represents a legal IPv4 or IPv6 address.

  Args:
    ip_string: The string to be tested.

  Returns:
    True if the string is a legal IP address, False otherwise.
  """
  try:
    ipaddress.ip_address(ip_string)
    return True
  except ValueError:
    return False


def is_valid_filepath(path):
    pieces = path.split('/')
   
    for idx in range(0,len(pieces)):
        if idx==0:  
            if pieces[0] not in ('.','..'):
                return False
            continue

        if pieces[idx].startswith('.') and pieces[idx] not in ('.','..'):
            return False

    return True


class NetCIDR():
    def __init__(self, row):
        self.name  = row[netNameIdx]
        self.intCIDR = row[netIntCIDRIdx]
        self.extCIDR = row[netExtCIDRIdx]

    def validate(self):
        if not validateFlag:
            return True, ""

        msgs = []

        intCIDRFound = len(self.intCIDR) > 0 and is_valid_cidr(self.intCIDR)
        extCIDRFound = len(self.extCIDR) > 0 and is_valid_cidr(self.extCIDR)

        if self.name not in netMap:
            msg = 'Network name {} not found in system model'.format(self.name)
            msgs.append(msg)
            intCIDRFound = False
            extCIDRFound = False

        if len(self.intCIDR)>0 and not is_valid_cidr(self.intCIDR):
            msg = 'Internal Network CIDR {} is not valid'.format(self.intCIDR)
            msgs.append(msg)
            cidrFound = False

        if len(self.extCIDR)>0 and not is_valid_cidr(self.extCIDR):
            msg = 'External Network CIDR {} is not valid'.format(self.extCIDR)
            msgs.append(msg)
            cidrFound = False

        # determine whether all IP addresses in associated devices are in that CIDR space
        if intCIDRFound:
            for device in networkDevices[self.name]:
                if len(device.intIP) >0 and not is_ip_in_cidr(device.intIP, self.intCIDR):
                    msg = 'internal IP of device {} attached to network {} not in network internal CIDR'.format(device.name, self.name)
                    msgs.append(msg)
            

        if extCIDRFound:
            for device in networkDevices[self.name]:
                if len(device.extIP) > 0 and not is_ip_in_cidr(device.extIP, self.extCIDR):
                    msg = 'external IP of device {} attached to network {} not in network external CIDR'.format(device.name, self.name)
                    msgs.append(msg)

        if intCIDRFound and extCIDRFound:
            intCIDR = ipaddress.ip_network(self.intCIDR, strict=False)
            extCIDR = ipaddress.ip_network(self.extCIDR, strict=False)
            if intCIDR.prefixlen != extCIDR.prefixlen:
                msg = 'internal and external CIDR representations for network {} do not match in size'.format(self.name)
                msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def repDict(self):
        if len(self.intCIDR) == 0 and len(self.extCIDR) == 0:
            return {}

        return {'network':self.name, 'intCIDR': self.intCIDR, 'extCIDR': self.extCIDR}



class DeviceIP():
    def __init__(self, row):
        self.name = row[devNameIdx]
        self.network = row[devNetIdx]
        self.intIP = row[devIntIPIdx]
        self.extIP = row[devExtIPIdx]

        if self.network not in networkDevices:
            networkDevices[self.network] = []
        networkDevices[self.network].append(self)

    def validate(self):
        if not validateFlag:
            return True, ""

        msgs = []

        netFound = True
        if self.network not in netMap:
            msg = 'Network name {} not found in system model'.format(self.network)
            msgs.append(msg)
            netFound = False

        if netFound and not self.name in netMap[self.network]:
            msg = 'Device name {} does not face network {} in system model'.format(self.name, self.network)
            msgs.append(msg)
           
        if not netFound:
            for net in netMap:
                if self.name in netMap[net]:
                    msg = 'Device name {} appears in network {} different in system model'.format(self.name, self.network)
                    msgs.append(msg)
 
        if len(self.intIP)>0 and not is_legal_ip_address(self.intIP):
            msg = 'Device {} internal IP address {} not in legal form'.format(self.name, self.intIP)
            msgs.append(msg)

        if len(self.intIP)>0 and not is_legal_ip_address(self.intIP):
            msg = 'Device {} internal IP address {} not in legal form'.format(self.name, self.intIP)
            msgs.append(msg)

        if len(self.extIP) > 0 and not is_legal_ip_address(self.extIP):
            msg = 'Device {} external IP address {} not in legal form'.format(self.name, self.extIP)
            msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def repDict(self):
        if len(self.intIP)==0 and len(self.extIP)==0:
            return {}
        return {'device':self.name, 'network':self.network, 'intIP': self.intIP, 'extIP': self.extIP}

class Feed():
    def __init__(self, row):
        self.name     = row[feedNameIdx]
        self.active   = row[feedActiveIdx]
        self.srctype  = row[feedSrcTypeIdx]
        self.srcspec  = row[feedSrcSpecIdx]
        self.time     = row[feedTimeIdx]
        self.dilation = row[feedDilationIdx]
        self.start    = row[feedStartIdx]

    def validate(self):
        if not validateFlag:
            return True, ""

        msgs = []
        if self.active not in ('true','True','false','False','T','F', '0','1',0,1):
            msg = 'Active designation {} should be boolean'.format(self.active)
            msgs.append(msg)

        if self.srctype not in ('file', 'unix-socket', 'net-socket'):
            msg = 'Feed source type must be "file", "unix-socket", or "net-socket"'.format(self.srctype)
            msgs.append(msg)

        elif self.srctype == 'unix-socket' and not os.path.isabs(self.srcspec):
            msg = 'unix-socket path string {} needs to describe an absolute file path'.format(self.srcspec)
            msgs.append(msg)

        if self.srctype == 'net-socket' and self.srcspec.startswith(':'): 
            colonspot = self.srcspec.find(':')
            port = self.srcspec[colonspot+1:]
            try:
                src_port = int(port)
                if src_port < 0:
                    msg = 'Socket number {} in source IP needs to be positive'.format(src_port)
                    msgs.append(msg)
                else:
                    foundSrc = True
            except:
                msg = 'Socket number {} in source IP needs to be positive integer'.format(src_port)
                msgs.append(msg)

        elif self.srctype == 'net-socket' and not self.srcspec.find(':') > 0:
            msg = 'Socket IP specification {} needs to give IP:port'.format(self.srcspec)
            msgs.append(msg)
 
        if self.time not in ('clock', 'packet'):
            msg = 'Time type {} should be "clock" or "packet"'.format(self.time)
            msgs.append(msg)

        isWallclock = self.time == 'clock'

        if not isWallclock: 
            try:
                dilation = float(self.dilation)
                if not dilation > 0.0:
                    msg = 'Dilation {} needs to be positive'.format(dilation)
                    msgs.append(msg)
            except:
                msg = 'Dilation {} needs to be positive floating point number'.format(self.dilation)
                msgs.append(msg)

            try:
                startTime = float(self.start)
                if startTime < 0.0:
                    msg = 'Start external packet arrival time {} needs to be non-negative'.format(startTime)
                    msgs.append(msg)
            except:
                msg = 'Start external packet arrival time {} needs to be numeric'.format(startTime)
                msgs.append(msg)

        if len(msgs) > 0:
            return False, '\n'.join(msgs)

        return True, ""

    def repDict(self):
        active = None
        if self.active in ('False','false','0',0,'F'):
            active = 0
        if self.active in ('True','true','1',1,'T'):
            active = 1

        if active is None:
            return {}

        srcspec = self.srcspec.replace(':','')
        return {'name':self.name, 'active':active, 'srctype':self.srctype, 'srcspec': srcspec,
            'time':self.time, 'dilation':float(self.dilation), 
            'start':float(self.start)}

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

    # attributes from which we get network names, and description of interfaces 
    parser.add_argument(u'-attrbDescIn', metavar = u'input json file of attributes to us in validation', 
            dest=u'attrbDesc_input', required=True)

    # outfile file of feed descriptors, used for validation in convert-cp.py
    parser.add_argument(u'-feedDescOut', metavar = u'output json file name of feed descriptions', 
        dest=u'feedDescOut', required=True)

    # output file of mapping table
    parser.add_argument(u'-ip', metavar = u'output file of ip mapping output', dest=u'ip_output', required=True)

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

    if args.validate is None:
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

    csv_input_file           = os.path.join(csvDir, args.csv_input)
    attrbDescIn_file         = os.path.join(descDir, args.attrbDesc_input)
    feedDescOut_file         = os.path.join(descDir, args.feedDescOut)
    ip_output_file           = os.path.join(yamlDir, args.ip_output)

    input_files = (csv_input_file, attrbDescIn_file)

    errs = 0
    for file_name in input_files:
        if not os.path.isfile(file_name):
            print_err('unable to open {} input file'.format(file_name))
            errs += 1 

    if errs>0:
        exit(1)
 
    try: 
        with open(attrbDescIn_file, 'r') as rf:
            attrbDesc = json.load(rf)
    except:
        print_err('unable to open {}'.format(attrbDescIn_file))
        exit(1)

    # build topology description map from interface description
    #  netMap map[string]map[string]
    #   index by network name to get map of devices facing that network  
    for netDict in attrbDesc['Network']:
        netMap[netDict['name']] = {}
        networkDevices[netDict['name']] = []
 
    for intrfcDict in attrbDesc['Interface']:
        network = intrfcDict['faces']
        device  = intrfcDict['device']
        name    = intrfcDict['name']
        
        if network not in netMap:
            netMap[network] = {}
        if device not in netMap[network]:
            netMap[network][device] = name
           
    deviceCode   = False
    networkCode = False
    feedCode    = False
    noneCode    = True
    
    with open(csv_input_file, newline='') as rf:
        csvrdr = csv.reader(rf)
        for raw in csvrdr:
            row = []
            for v in raw:
                row.append(v.strip())

            if noneCode or deviceCode:
                row = row[:devExtIPIdx+1]
            elif networkCode: 
                row = row[:netExtCIDRIdx+1]
            else:
                row = row[:feedStartIdx+1]

            if row[0].find('#') > -1:
                continue

            if empty(row):
                continue

            if unnamed(row):
                continue

            row = cleanRow(row)

            rowTypes = ["Device", "Network", "Feed"]
            typeSeen = {"Device": False, "Network": False, "Feed": False}

            codeTransition = False
            for rowtype in rowTypes:
                if not typeSeen[rowtype] and rowtype == "Device" and row[0] == rowtype: 
                    deviceCode = True
                    networkCode = False
                    feedCode   = False
                    noneCode = False
                    codeTransition = True
                    typeSeen[rowtype] = True
                    break

                if not typeSeen[rowtype] and rowtype == "Network" and row[0] == rowtype:
                    networkCode = True
                    deviceCode = False
                    feedCode   = False
                    noneCode = False
                    codeTransition = True
                    typeSeen[rowtype] = True
                    break

                if not typeSeen[rowtype] and rowtype == "Feed" and row[0] == rowtype:
                    networkCode = False
                    deviceCode = False
                    feedCode   = True
                    noneCode = False
                    codeTransition = True
                    typeSeen[rowtype] = True
                    break

            if codeTransition:
                codeTransition = False
                continue

            if deviceCode:
                deviceList.append(DeviceIP(row))
                continue

            if networkCode:
                netList.append(NetCIDR(row))
                continue

            if feedCode:
                feedList.append(Feed(row))
                continue
        
    msgs = []
    for net in netList:
        valid, msg = net.validate()
        if not valid:
            msgs.append(msg)

    for device in deviceList:
        valid, msg = device.validate()
        if not valid:
            msgs.append(msg)

    feedsrcspec = {}
    feedDescDict = {}

    for feed in feedList:
        valid, msg = feed.validate()
        if not valid:
            msgs.append(msg)
        else:
            if feed.srcspec in feedsrcspec:
                msg = 'Feed {} has feed specification that matches another'.format(feed.name)
                msgs.append(msg)
            feedsrcspec[feed.srcspec] = True 

        if feed.name in feedDescDict:
            msg = 'Feed name {} appears multiple times'.format(feed.name)
            msgs.append(msg)
        else:
            feedDescDict[feed.name] = {'srctype': feed.srctype, 'time':feed.time, 'start':feed.start}

    if len(msgs) > 0 :
        for msgrp in msgs:
            msgrp = msgrp.split('\n')
            for msg in msgrp:
                print_err(msg)

        exit(1)

    # create the output 
    ipDict = {'networks':[], 'devices':[], 'feeds':[]}
    for net in netList:
        rd = net.repDict()
        if len(rd) > 0 :
            ipDict['networks'].append(rd)
    
    for device in deviceList:
        rd = device.repDict()
        if len(rd) > 0 :
            ipDict['devices'].append(rd)

    for feed in feedList:
        rd = feed.repDict()
        if len(rd) > 0 :
            ipDict['feeds'].append(rd)

    with open(ip_output_file, 'w') as wf:
        yaml.dump(ipDict, wf)

    with open(feedDescOut_file, 'w') as wf:
        json.dump(feedDescDict, wf)

def cleanRow(row):
    rtn = []
    for r in row:
        if r.startswith('#!'):
            r = ''                     
        elif len(rtn) > 0 and r.startswith('#'):
            break
        rtn.append(r.strip())

    return rtn

if __name__ == '__main__':
    main()
