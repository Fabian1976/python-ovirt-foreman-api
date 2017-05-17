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
import collections #to order dict by key
import puppet #REST API for puppetserver

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/lib')
import api_ovirt
import api_foreman
import api_zookeeper
import api_vmware

vm_config = None
zk_base_path = '/puppet'
from config import Config
import simplecrypt
import base64
#disable warnings urllib
import warnings
warnings.simplefilter('ignore')
#disable warnings Foreman API
import logging
logging.disable(logging.ERROR)

def rebuildVMs():
    for vm in vm_config.vm_list:
        vm_info = vm_config.vm_list[vm]

        print "*" * sum((12, len(vm_info['vm_fqdn'])))
        print "***** " + vm_info['vm_fqdn'] + " *****"
        print "*" * sum((12, len(vm_info['vm_fqdn'])))

        print " - Connect to Foreman"
        foreman_conn = api_foreman.connectToHost(vm_info["foreman"], vm_info["foreman_user"], simplecrypt.decrypt(vm_config.salt, base64.b64decode(vm_info['foreman_password'])))
        result = api_foreman.buildHost(foreman_conn, vm_info['vm_fqdn'])
        if result != "Host '%s' successfully set to build mode" % vm_info['vm_fqdn']:
            print "   - " + result
            print "Finished unsuccesfully, aborting"
            sys.exit(99)
        print "   -", result
        print " - Connect to Puppetmaster"
        puppet_conn = puppet.Puppet(host=vm_config.puppetmaster_address, port=vm_config.puppetmaster_port, key_file='./ssl/api-key.pem', cert_file='./ssl/api-cert.pem')
        print "   - Clear certificate of %s" % vm_info['vm_fqdn']
        try:
            puppet_conn.certificate_clean(vm_info['vm_fqdn'])
        except Exception as e:
            print e
            #ignore if certificate doesn't exist
            pass
        print " - Connect to hypervisor"
        ovirt_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], simplecrypt.decrypt(vm_config.salt, base64.b64decode(vm_info['hypervisor_password'])))
        print "   - Setting host to PXE boot"
        api_ovirt.setPXEBootFirst(ovirt_conn, vm_info['vm_fqdn'])
        print "   - Rebooting host"
        api_ovirt.hardRebootGuest(ovirt_conn, vm_info['vm_fqdn'])
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
    print "These VM's will be reset to their default provisioning:"
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
        rebuildVMs()
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
