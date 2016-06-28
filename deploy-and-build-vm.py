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
import collections #to order dict by key

vm_config = None
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
                vm_list[section]['vm_domain'] = self.config.get(section, 'vm_domain')
            except:
                print "No domain provided. Assuming default of 'localdomain'"
                vm_list[section]['vm_domain'] = 'localdomain'
            vm_list[section]['vm_fqdn'] = section + '.' + vm_list[section]['vm_domain']
            try:
                vm_list[section]['vm_cluster'] = self.config.get(section, 'vm_cluster')
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
                vm_list[section]['vm_datastore'] = self.config.get(section, 'vm_datastore')
            except:
                print "No datastore provided. Cannot continue"
                sys.exit(99)
            try:
                vm_list[section]['vm_memory'] = self.config.get(section, 'vm_memory')
            except:
                print "No memory provided. Assumning default of 512 MB"
                vm_list[section]['vm_memory'] = 512
            try:
                vm_list[section]['vm_cpus'] = self.config.get(section, 'vm_cpus')
            except:
                print "No number of cpu's provided. Assuming default of 1"
                vm_list[section]['vm_cpus'] = 1
            try:
                vm_list[section]['vm_disks'] = self.config.get(section, 'vm_disks').split(',')
            except:
                print "No disks provided. Assuming single disk of 16 GB"
                vm_list[section]['vm_disks'] = ['16']
            try:
                vm_list[section]['vm_purpose'] = self.config.get(section, 'vm_purpose')
            except:
                vm_list[section]['vm_purpose'] = ''
            try:
                vm_list[section]['vm_network'] = self.config.get(section, 'vm_network')
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
                vm_list[section]['foreman_ptable'] = self.config.get(section, 'foreman_ptable')
            except:
                print "No foreman partition table provided. Assuming default 'Kickstart default'"
                vm_list[section]['foreman_ptable'] = 'Kickstart default'
            try:
                vm_list[section]['puppet_environment'] = self.config.get(section, 'puppet_environment')
            except:
                print "No puppet environment provided. Assuming default of 'production'"
                vm_list[section]['puppet_environment'] = 'production'
            try:
                vm_list[section]['puppet_server_role'] = self.config.get(section, 'puppet_server_role')
            except:
                print "No server role provided. The base role will be the only one applied to this server"
                vm_list[section]['puppet_server_role'] = ''
            self.vm_list = vm_list

def createRoleZookeeper(node_name, puppet_environment, puppet_server_role):
    zk_path = zk_base_path + '/' + puppet_environment + '/nodes/' + node_name + '/roles'
    zk = kazoo.client.KazooClient(hosts='zookeeper01.core.cmc.lan:2181')
    zk.start()
    zk.ensure_path(zk_path)
    zk.set(zk_path, puppet_server_role.encode())
    zk.stop()
    zk.close()

def createVMs():
    for vm in vm_config.vm_list:
        vm_info = vm_config.vm_list[vm]

        print " - Connect to hypervisor"
        ovirt_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], vm_info['hypervisor_password'])
        print " - Connect to Foreman"
        foreman_conn = api_foreman.connectToHost(vm_info["foreman"], vm_info["foreman_user"], vm_info['foreman_password'])

        print "*" * sum((12, len(vm_info['vm_fqdn'])))
        print "***** " + vm_info['vm_fqdn'] + " *****"
        print "*" * sum((12, len(vm_info['vm_fqdn'])))

        print " - Create VM on hypervisor"
        print "   - hypervisor:", vm_info["hypervisor"]
        print "   - datastore:", vm_info["vm_datastore"]
        print "   - name:", vm_info['vm_fqdn']
        print "   - domain:", vm_info['vm_domain']
        print "   - #cpu:", vm_info["vm_cpus"]
        print "   - memory:", vm_info["vm_memory"],"MB"
        print "   - disks:"
        for disk in vm_info["vm_disks"]:
            print "     - " + disk + "GB"
        print "   - vlan:", vm_info['vm_network']
        print ""
        result = api_ovirt.createGuest(ovirt_conn, vm_info["vm_cluster"], vm_info['vm_fqdn'], vm_info["vm_purpose"], int(vm_info["vm_memory"]), int(vm_info["vm_cpus"]), vm_info["vm_disks"], vm_info["vm_datastore"], vm_info["vm_network"])
        if result != "Succesfully created guest: " + vm_info['vm_fqdn']:
            print result
            print "Finished unsuccesfully, aborting"
            ovirt_conn.disconnect()
            sys.exit(99)
        print " -", result

        print " - Retrieve MAC address to pass to foreman"
        vm_mac = api_ovirt.getMac(ovirt_conn, vm_info['vm_fqdn'])
        print "   - Found MAC: %s" % vm_mac
        print " - Create host in foreman"
        print "   - foreman:", vm_info['foreman']
        print "   - hostgroup:", vm_info['foreman_hostgroup']
        print "   - organization:", vm_info['foreman_organization']
        print "   - location:", vm_info['foreman_location']
        print "   - subnet:", vm_info['foreman_subnet']
        print "   - puppet environment:", vm_info['puppet_environment']
        print ""
        result = api_foreman.createGuest(foreman_conn, vm, vm_info['foreman_hostgroup'], vm_info['vm_domain'], vm_info['foreman_organization'], vm_info['foreman_location'], vm_mac, vm_info['foreman_subnet'], vm_info['puppet_environment'], vm_info['foreman_ptable'], 'true')
        if result != "Succesfully created guest: " + vm:
            print result
            print "Finished unsuccesfully, aborting"
            sys.exit(99)
        print " -", result
        print " - Creating role in Zookeeper"
        print "   - server role:", vm_info['puppet_server_role']
        createRoleZookeeper(vm_info['vm_fqdn'], vm_info['puppet_environment'], vm_info['puppet_server_role'])
        print " - Starting VM %s" % vm_info['vm_fqdn']
        api_ovirt.powerOnGuest(ovirt_conn, vm_info['vm_fqdn'])
    print " - Disconnect from hypervisor"
    ovirt_conn.disconnect()

def main():
    global vm_config

    #file to read
    if len(sys.argv) == 2:
        fname = sys.argv[1]
    else:
        print "Give an input file as argument..."
        sys.exit(99)
    vm_config = Config(fname)
    vm_config.parse()
    print "These VM's will be created:"
    for vm in vm_config.vm_list:
        print '- ' + vm
        for key, value in collections.OrderedDict(sorted(vm_config.vm_list[vm].items())).items():
            if not isinstance(value, list):
                print '\t- %s: %s' % (key, value)
            else:
                print '\t- %s:' % key
                for v in value:
                    print '\t\t- %s' % v
    print "Is this correct? (y/n)"
    answer = raw_input().lower()
    if answer == 'y':
        os.system('clear')
        createVMs()
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
