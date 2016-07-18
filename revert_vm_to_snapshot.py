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
import ConfigParser
import collections #to order dict by key

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/lib')
import api_ovirt
from config import Config

vm_config = None

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
