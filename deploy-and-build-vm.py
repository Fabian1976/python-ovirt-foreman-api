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
import ConfigParser

zk_base_path = '/puppet'

class Config:
    def __init__(self, conf_file):
        self.conf_file = conf_file
        self.vm_list = {}
        if not os.path.exists(self.conf_file):
            print "Can't open config file '%s'" % self.conf_file
            sys.exit(1)

        self.config = ConfigParser.ConfigParser()
        self.config.read(self.conf_file)

    def parse(self):
        sections = self.config.sections()
        vm_list = {}
        for section in sections:
            vm_list[section] = {}
            try:
                vm_list[section]['domain'] = self.config.get(section, 'domain')
            except:
                print "No domain provided. Assuming default of 'localdomain'"
                vm_list[section]['domain'] = 'localdomain'
            try:
                vm_list[section]['cluster'] = self.config.get(section, 'cluster')
            except:
                print "No cluster parameter provided. Cannot continue"
                sys.exit(99)
            try:
                vm_list[section]['hypervisor'] = self.config.get(section, 'hypervisor')
            except:
                print "No hypervisor provided. Cannot continue"
                sys.exit(99)
            try:
                vm_list[section]['hypervisor_user'] = self.config.get(section, 'hypervisor_user')
            except:
                print "No user specified for hypervisor access. Cannot continue"
                sys.exit(99)
            try:
                vm_list[section]['hypervisor_password'] = self.config.get(section, 'hypervisor_password')
            except:
                print "No hypervisor password provided. Please provide one:"
                vm_list[section]['hypervisor_password'] = getpass.getpass("  enter password for hypervisor " + vm_list[section]['hypervisor'] + " and user " + vm_list[section]['hypervisor_user'] + " to continue: ")
            try:
                vm_list[section]['datastore'] = self.config.get(section, 'datastore')
            except:
                print "No datastore provided. Cannot continue"
                sys.exit(99)
            try:
                vm_list[section]['memory'] = self.config.get(section, 'memory')
            except:
                print "No memory provided. Assumning default of 512 MB"
                vm_list[section]['memory'] = 512
            try:
                vm_list[section]['cpus'] = self.config.get(section, 'cpus')
            except:
                print "No number of cpu's provided. Assuming default of 1"
                vm_list[section]['cpus'] = 1
            try:
                vm_list[section]['disksize'] = self.config.get(section, 'disksize')
            except:
                print "No disksize provided. Assuming default of 16 GB"
                vm_list[section]['disksize'] = 16
            try:
                vm_list[section]['purpose'] = self.config.get(section, 'purpose')
            except:
                vm_list[section]['purpose'] = ''
            try:
                vm_list[section]['network'] = self.config.get(section, 'network')
            except:
                print "No VLAN provided. You can still access the VM, but only through the console."
            try:
                vm_list[section]['foreman'] = self.config.get(section, 'foreman')
            except:
                print "No foreman host provided. Cannot continue"
                sys.exit(99)
            try:
                vm_list[section]['foreman_user'] = self.config.get(section, 'foreman_user')
            except:
                print "No foreman user provided. Cannot continue"
            try:
                vm_list[section]['foreman_password'] = self.config.get(section, 'foreman_password')
            except:
                print "No foreman password provided. Please provide one:"
                vm_list[section]['foreman_password'] = getpass.getpass("  enter password for foreman " + vm_list[section]['foreman'] + " and user " + vm_list[section]['foreman_user'] + " to continue: ")
            try:
                vm_list[section]['foreman_hostgroup'] = self.config.get(section, 'foreman_hostgroup')
            except:
                print "No foreman hostgroup provided. Assuming default of 'CentOS7 Minimal'"
                vm_list[section]['foreman_hostgroup'] = 'CentOS7 Minimal'
            try:
                vm_list[section]['foreman_organization'] = self.config.get(section, 'foreman_organization')
            except:
                print "No foreman organization provided. Assumning default of 'CMC'"
                vm_list[section]['foreman_organization'] = 'CMC'
            try:
                vm_list[section]['foreman_location'] = self.config.get(section, 'foreman_location')
            except:
                print "No foreman location provided. Cannot continue"
                sys.exit(99)
            try:
                vm_list[section]['foreman_subnet'] = self.config.get(section, 'foreman_subnet')
            except:
                print "No foreman subnet provided. You can still access the VM, but only through the concole"
            try:
                vm_list[section]['puppet_environment'] = self.config.get(section, 'puppet_environment')
            except:
                print "No puppet environment provided. Assuming default of 'production'"
                vm_list[section]['puppet_environment'] = 'production'
            try:
                vm_list[section]['server_role'] = self.config.get(section, 'server_role')
            except:
                print "No server role provided. The base role will be the only one applied to this server"
                vm_list[section]['server_role'] = ''
            self.vm_list = vm_list

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
        vm_info = vm_list[vm]
        guest_name = vm

        print " - Connect to hypervisor"
        ovirt_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], vm_info['hypervisor_password'])
        print " - Connect to Foreman"
        foreman_conn = api_foreman.Foreman('http://'+vm_info["foreman"], (vm_info["foreman_user"], vm_info['foreman_password']), api_version = 2)

        print "*" * sum((12, len(guest_name)))
        print "***** " + guest_name + " *****"
        print "*" * sum((12, len(guest_name)))

        print " - Create VM on hypervisor"
        print "   - hypervisor:", vm_info["hypervisor"]
        print "   - datastore:", vm_info["datastore"]
        print "   - name:", guest_name
        print "   - domain:", vm_info['domain']
        print "   - #cpu:", vm_info["cpus"]
        print "   - memory:", vm_info["memory"],"MB"
        print "   - diskspace:", vm_info["disksize"],"GB"
        print "   - vlan:", vm_info['network']
        print ""
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
        print "   - foreman:", vm_info['foreman']
        print "   - hostgroup:", vm_info['foreman_hostgroup']
        print "   - organization:", vm_info['foreman_organization']
        print "   - location:", vm_info['foreman_location']
        print "   - subnet:", vm_info['foreman_subnet']
        print "   - puppet environment:", vm_info['puppet_environment']
        print ""
        result = api_foreman.createGuest(foreman_conn, guest_name, vm_info['foreman_hostgroup'], vm_info['domain'], vm_info['foreman_organization'], vm_info['foreman_location'], vm_mac, vm_info['foreman_subnet'], vm_info['puppet_environment'], 'true')
        if result != "Succesfully created guest: " + guest_name:
            print result
            print "Finished unsuccesfully, aborting"
            sys.exit(99)
        print " -", result
        print " - Creating role in Zookeeper"
        print "   - server role:", vm_info['server_role']
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
    vm_config = Config(fname)
    vm_config.parse()
#    vm_list = vm_config.vm_list
#    for vm in vm_list:
#        print vm
#        print vm_list[vm]['foreman']
#    sys.exit(1)

    createVMs(vm_config.vm_list)

if __name__ == '__main__':
    main()
