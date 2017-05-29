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

def deleteZookeeperPath(path, recursive=False):
    zk = kazoo.client.KazooClient(hosts=vm_config.zookeeper_address + ':' + vm_config.zookeeper_port)
    zk.start()
    zk.delete(path, recursive=recursive)
    zk.stop()
    zk.close()

def getZookeeperValue(path):
    zk = kazoo.client.KazooClient(hosts=vm_config.zookeeper_address + ':' + vm_config.zookeeper_port)
    zk.start()
    value = zk.get(path)
    zk.stop()
    zk.close()
    return value

def destroyVMs():
    for vm in vm_config.vm_list:
        vm_info = vm_config.vm_list[vm]
        print " - Connect to hypervisor"
        if vm_info['hypervisor_type'].lower() in ['ovirt', 'rhev']:
            hypervisor_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], simplecrypt.decrypt(vm_config.salt, base64.b64decode(vm_info['hypervisor_password'])))
        else:
            hypervisor_conn = api_vmware.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], simplecrypt.decrypt(vm_config.salt, base64.b64decode(vm_info['hypervisor_password'])))
        #determine how to name VM
        if vm_config.use_fqdn_as_name == 0:
            vm_name = vm
        else:
            vm_name = vm_info['vm_fqdn']

        print "*" * sum((12, len(vm_name)))
        print "***** " + vm_name + " *****"
        print "*" * sum((12, len(vm_name)))

        if vm_info['hypervisor_type'].lower() in ['ovirt', 'rhev']:
            result = api_ovirt.destroyGuest(hypervisor_conn, vm_name)
        else:
            result = api_vmware.destroyGuest(hypervisor_conn, vm_name)
#        if result != "Succesfully removed guest: " + vm_name:
#            print result
#            print "Finished unsuccesfully, aborting"
#            hypervisor_conn.disconnect()
#            sys.exit(99)
        print " -", result

        print " - Connect to Foreman"
        foreman_conn = api_foreman.connectToHost(vm_info["foreman"], vm_info["foreman_user"], simplecrypt.decrypt(vm_config.salt, base64.b64decode(vm_info['foreman_password'])))
        result = api_foreman.destroyGuest(foreman_conn, vm_info['vm_fqdn'])
        if result != "Succesfully removed guest: " + vm_info['vm_fqdn']:
            print "   - ", result
            print "Finished unsuccesfully, aborting"
            sys.exit(99)
        print "   - ", result
        print " - Connect to Puppetmaster"
        puppet_conn = puppet.Puppet(host=vm_config.puppetmaster_address, port=vm_config.puppetmaster_port, key_file='./ssl/api-key.pem', cert_file='./ssl/api-cert.pem')
        print "   - Clear certificate of %s" % vm_info['vm_fqdn']
        try:
            puppet_conn.certificate_clean(vm_info['vm_fqdn'])
        except Exception as e:
            print e
            #ignore if certificate doesn't exist
            pass
        print " - Connect to zookeeper"
        zookeeper_conn = api_zookeeper.connectToHost(vm_config.zookeeper_address, vm_config.zookeeper_port)
        print " - Zookeeper records"
        if vm_info['ossec_in_env'] == 1:
            print "   - Get ossec server IP"
            ossecserver, nodeStats = api_zookeeper.getValue(zookeeper_conn, zk_base_path + '/' + vm_info['puppet_environment'] + '/defaults/core::profile::ossec::client::ossec_server')
            print "   - Delete zookeeper ossec auth"
            zk_path = zk_base_path + '/production/nodes/' + ossecserver + '/client-keys/' + vm_info['vm_fqdn']
            result = api_zookeeper.deleteValue(zookeeper_conn, zk_path, recursive=True)
            if result != "Succesfully deleted path '%s'" % zk_path:
                print result
                print "Finished unsuccesfully, aborting"
                sys.exit(99)
        print "   - Delete zookeeper puppet node"
        zk_path = zk_base_path + '/' + vm_info['puppet_environment'] + '/nodes/' + vm_info['vm_fqdn']
        result = api_zookeeper.deleteValue(zookeeper_conn, zk_path, recursive=True)
        if result != "Succesfully deleted path '%s'" % zk_path:
            print result
            print "Finished unsuccesfully, aborting"
            sys.exit(99)
    if vm_config.vm_type.lower() == 'oracle-rac':
        #delete shared disks from first vm
        for vm in sorted(vm_config.vm_list.keys()):
            vm_info = vm_config.vm_list[vm]
            #determine how to name VM
            if vm_config.use_fqdn_as_name == 0:
                vm_name = vm
            else:
                vm_name = vm_info['vm_fqdn']

            disk_counter = 1
            if vm_info['hypervisor_type'].lower() in ['ovirt', 'rhev']:
                for disk in vm_config.shared_disks:
                    api_ovirt.deleteDisk(hypervisor_conn, vm_name+'_racdisk'+str(disk_counter).zfill(2))
                    disk_counter += 1
            break

    print " - Disconnect from hypervisor"
    hypervisor_conn.disconnect()
    print " - Disconnect from zookeeper"
    api_zookeeper.disconnect(zookeeper_conn)

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
