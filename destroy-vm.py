#!/usr/bin/python
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
            if section == 'common':
                try:
                    self.unattended = self.config.get(section, 'unattended')
                except:
                    print 'Run unattended not specified. Assuming NO'
                    self.unattended = '0'
            else:
                vm_list[section] = {}
                try:
                    vm_list[section]['vm_domain'] = self.config.get(section, 'vm_domain')
                except:
                    print "No domain provided. Assuming default of 'localdomain'"
                    vm_list[section]['vm_domain'] = 'localdomain'
                vm_list[section]['vm_fqdn'] = section + '.' + vm_list[section]['vm_domain']
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
                self.vm_list = vm_list

def destroyVMs():
    for vm in vm_config.vm_list:
        vm_info = vm_config.vm_list[vm]

        print " - Connect to hypervisor"
        ovirt_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], vm_info['hypervisor_password'])

        print "*" * sum((12, len(vm_info['vm_fqdn'])))
        print "***** " + vm_info['vm_fqdn'] + " *****"
        print "*" * sum((12, len(vm_info['vm_fqdn'])))

        result = api_ovirt.destroyGuest(ovirt_conn, vm_info['vm_fqdn'])
        if result != "Succesfully removed guest: " + vm_info['vm_fqdn']:
            print result
            print "Finished unsuccesfully, aborting"
            ovirt_conn.disconnect()
            sys.exit(99)
        print " -", result

        print " - Connect to Foreman"
        foreman_conn = api_foreman.connectToHost(vm_info["foreman"], vm_info["foreman_user"], vm_info['foreman_password'])
        result = api_foreman.destroyGuest(foreman_conn, vm_info['vm_fqdn'])
        if result != "Succesfully removed guest: " + vm_info['vm_fqdn']:
            print result
            print "Finished unsuccesfully, aborting"
            sys.exit(99)
        print " -", result
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
    print "These VM's will be destroyed (PERMANENTLY!!):"
    for vm in vm_config.vm_list:
        print '- ' + vm
        for key, value in collections.OrderedDict(sorted(vm_config.vm_list[vm].items())).items():
            if not isinstance(value, list):
                print '\t- %s: %s' % (key, value)
            else:
                print '\t- %s:' % key
                for v in value:
                    print '\t\t- %s' % v
    if vm_config.unattended == '0':
        print "Is this correct? (y/n)"
        answer = raw_input().lower()
    else:
        answer = 'y'
    if answer == 'y':
        os.system('clear')
        destroyVMs()
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
