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
import ConfigParser
import collections #to order dict by key

vm_config = None

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
                    vm_list[section]['snapshot_to_restore'] = self.config.get(section, 'snapshot_to_restore')
                except:
                    print "No snapshot to restore provided. Cannot continue"
                    sys.exit(99)
                try:
                    vm_list[section]['boot_after_restore'] = self.config.get(section, 'boot_after_restore')
                except:
                    print "Boot after restore not specified. Assuming NO"
                    vm_list[section]['boot_after_restore'] = '0'
                self.vm_list = vm_list

def revertToSnapshots():
    for vm in vm_config.vm_list:
        vm_info = vm_config.vm_list[vm]
        ovirt_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], vm_info['hypervisor_password'])
        api_ovirt.revertToSnapshot(ovirt_conn, vm_info['vm_fqdn'], vm_info['snapshot_to_restore'], vm_info['boot_after_restore'])
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
    print "These VM's will be reverted to their snapshot:"
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
        revertToSnapshots()
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
