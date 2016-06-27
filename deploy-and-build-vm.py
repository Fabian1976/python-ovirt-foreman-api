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
from kazoo.client import KazooClient #Zookeeper client class
import kazoo #Zookeeper class

zk_base_path = '/puppet'

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
                key, value = line.split("=")
                vm_list[guest_name][key.strip()] = value.strip()
    f.close()
    return vm_list

def createRoleZookeeper(node_name, puppet_environment, server_role):
    zk_path = zk_base_path + '/' + puppet_environment + '/nodes/' + node_name + '/roles'
    zk = kazoo.client.KazooClient(hosts='zookeeper01.core.cmc.lan:2181')
    zk.start()
    zk.ensure_path(zk_path)
    zk.set(zk_path, server_role.encode())
    zk.stop()
    zk.close()

def createVMs(vm_list):
    for vm in vm_list:
        print "*"*sum((12, len(vm)))
        print "***** "+vm+" *****"
        print "*"*sum((12, len(vm)))
        vm_info = vm_list[vm]

        print " - Connect to hypervisor"
        hypervisor_pwd = getpass.getpass("  enter password for user " + vm_info["hypervisor_user"] + " to continue: ")
        ovirt_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], hypervisor_pwd)
        print " - Connect to Foreman"
        foreman_pwd = getpass.getpass("  enter password for user " + vm_info["foreman_user"] + " to continue: ")
        foreman_conn = api_foreman.Foreman('http://'+vm_info["foreman"], (vm_info["foreman_user"], foreman_pwd), api_version = 2)

        guest_name = vm

        print " - Create VM on hypervisor"
        print "   - hypervisor:", vm_info["hypervisor"]
        print "   - datastore:", vm_info["datastore"]
        print "   - name:", guest_name
        print "   - #cpu:", vm_info["cpus"]
        print "   - memory:", vm_info["memory"],"MB"
        print "   - diskspace:", vm_info["disksize"],"GB"

        result = api_ovirt.createGuest(ovirt_conn, vm_info["cluster"], guest_name + '.' + vm_info['domain'], vm_info["purpose"], int(vm_info["memory"]), int(vm_info["cpus"]), int(vm_info["disksize"]), vm_info["datastore"], vm_info["network"])
        if result != "Succesfully created guest: " + guest_name + '.' + vm_info['domain']:
            print result
            print "Finished unsuccesfully, aborting"
            ovirt_conn.disconnect()
            sys.exit(99)
        print " -", result

        print " - Retrieve MAC address to pass to foreman"
        vm_mac = api_ovirt.getMac(ovirt_conn, guest_name + '.' + vm_info['domain'])
        print "   - Found MAC: %s" % vm_mac
        print " - Create host in foreman"
        result = api_foreman.createGuest(foreman_conn, guest_name, vm_info['foreman_hostgroup'], vm_info['domain'], vm_info['foreman_organization'], vm_info['foreman_location'], vm_mac, vm_info['foreman_subnet'], vm_info['puppet_environment'], 'true')
        if result != "Succesfully created guest: " + guest_name:
            print result
            print "Finished unsuccesfully, aborting"
            sys.exit(99)
        print " -", result
        print " - Creating role in Zookeeper"
        createRoleZookeeper(guest_name + '.' + vm_info['domain'], vm_info['puppet_environment'], vm_info['server_role'])
        print " - Starting VM %s" % guest_name
        api_ovirt.powerOnGuest(ovirt_conn, guest_name + '.' + vm_info['domain'])
    print " - Disconnect from hypervisor"
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

if __name__ == '__main__':
    main()
