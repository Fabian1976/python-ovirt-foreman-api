#!/usr/bin/python

# Created by Jens Depuydt
# http://www.jensd.be
# http://github.com/jensdepuydt

import sys
import os
import getpass
import datetime
import time
import commands
import json
import urllib2
import string
import random
import crypt
import getpass
import api_ovirt
import api_foreman

def readVMs(fname):
    #read contents of input file and put it in dict
    f = open(fname, "r")
    vm_list = {}
    for line in f:
        line = line.strip()
        #ignore comments
        if not line.startswith("#") and line:
            if line.startswith("[") and line.endswith("]"):
                guest_name = line[1:-1]
                vm_list[guest_name] = {}
            else:
                key, value = line.split(":")
                vm_list[guest_name][key.strip()] = value.strip()
    f.close()
    return vm_list

def createVMs(vm_list):
    for vm in vm_list:
        print "*"*sum((12, len(vm)))
        print "***** "+vm+" *****"
        print "*"*sum((12, len(vm)))
        vm_info = vm_list[vm]

        print " - Connect to hypervisor"
        hypervisor_pwd = getpass.getpass("  enter password for user " + vm_info["hypervisor_user"] + " to continue: ")
        ovirt_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], hypervisor_pwd)
#        print " - Connect to Foreman"
#        foreman_pwd = getpass.getpass("  enter password for user " + vm_info["foreman_user"] + " to continue: ")
#        foreman_conn = api_foreman.Foreman('http://'+vm_info["foreman"], (vm_info["foreman_user"], foreman_pwd), api_version = 2)

        guest_name = vm

        print " - Create VM on hypervisor"
        print "   - hypervisor:", vm_info["hypervisor"]
        print "   - datastore:", vm_info["datastore"]
        print "   - name:", guest_name
        print "   - #cpu:", vm_info["cpus"]
        print "   - memory:", vm_info["memory"],"MB"
        print "   - diskspace:", vm_info["disksize"],"GB"

        result = api_ovirt.createGuest(ovirt_conn, vm_info["cluster"], guest_name, vm_info["purpose"], int(vm_info["memory"]), int(vm_info["cpus"]), int(vm_info["disksize"]), vm_info["datastore"], vm_info["network"])
        if result != "Succesfully created guest: " + guest_name:
            print result
            print "Finished unsuccesfully, aborting"
            ovirt_conn.disconnect()
            sys.exit(99)
        print " -", result

        print " - Retrieve MAC address to pass to foreman"
        vm_mac = api_ovirt.getMac(ovirt_conn, guest_name)
        print "   - Found MAC: %s" % vm_mac
#        print " - Create host in foreman"
#        result = api_foreman.createGuest(foreman_conn, guest_name, vm_info['foreman_hostgroup'], vm_info['domain'], vm_info['foreman_organization'], vm_info['foreman_location'], vm_mac, vm_info['foreman_subnet'], vm_info['puppet_environment'], guest_build='true')
#        if result != "Succesfully created guest: " + guest_name:
#            print result
#            print "Finished unsuccesfully, aborting"
#            sys.exit(99)
#        print " -", result
#        print " - Starting VM %s" % guest_name
#        api_ovirt.powerOnGuest(ovirt_conn, guest_name)
    print " - Disconnect from hypervisor"
    ovirt_conn.disconnect()

def write_dsc_files(vm_list):
    for vm in vm_list:
        vm_info = vm_list[vm]
        hypervisor_pwd = getpass.getpass("  enter password for user " + vm_info["hypervisor_user"] + " to continue: ")
        ovirt_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], hypervisor_pwd)
        print "$Hostname = '%s'" % vm
        print "$vDC = '%s'" % vm.split('-')[0]
        print "$MAC = '%s'" % api_ovirt.getMac(ovirt_conn, vm)
        print "$IP = '%s'" % vm_info['ipaddress']
        print "$Role = '%s'" % vm_info['role'].upper()
        print "$OTAP = 'P'"
        print "$PuppetAgent_Arguments = 'PUPPET_MASTER_SERVER=puppetmaster01.core.cmc.lan PUPPET_AGENT_ENVIRONMENT=%s'" % vm_info["puppet_environment"]
        f = open('/mnt/dsc/' + vm + '.start', "w")
        f.write("$Hostname = '%s'\r\n" % vm)
        f.write("$vDC = '%s'\r\n" % vm.split('-')[0])
        f.write("$MAC = '%s'\r\n" % api_ovirt.getMac(ovirt_conn, vm))
        f.write("$IP = '%s'\r\n" % vm_info['ipaddress'])
        f.write("$Role = '%s'\r\n" % vm_info['role'].upper())
        f.write("$OTAP = 'P'\r\n")
        f.write("$PuppetAgent_Arguments = 'PUPPET_MASTER_SERVER=puppetmaster01.core.cmc.lan PUPPET_AGENT_ENVIRONMENT=%s'\r\n" % vm_info["puppet_environment"])
        f.close()
    ovirt_conn.disconnect()

def main():
    #file to read
    if len(sys.argv) == 2:
        fname = sys.argv[1]
    else:
        print "Give an input file as argument..."
        sys.exit(99)
    vm_list = readVMs(fname)
    createVMs(vm_list)
    write_dsc_files(vm_list)

if __name__ == '__main__':
        main()
