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
from kazoo.client import KazooClient #Zookeeper client class
import kazoo #Zookeeper class
import collections #to order dict by key
import puppet #REST API for puppetserver

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/lib')
import api_ovirt
import api_foreman

vm_config = None
zk_base_path = '/puppet'
from config import Config

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
        print " - Connect to Puppetmaster"
        puppet_conn = puppet.Puppet(host='puppetmaster01.core.cmc.lan', port=8140, key_file='./ssl/api-key.pem', cert_file='./ssl/api-cert.pem')
        print "   - Clear certificate of %s" % vm_info['vm_fqdn']
        puppet_conn.certificate_clean(vm_info['vm_fqdn'])
        print " - Zookeeper records"
        print "   - Get ossec server IP"
        ossecserver, nodeStats = getZookeeperValue(zk_base_path + '/' + vm_info['puppet_environment'] + '/defaults/profile::ossec::client::ossec_server')
        print "   - Delete zookeeper ossec auth"
        deleteZookeeperPath(zk_base_path + '/production/nodes/' + ossecserver + '/client-keys/' + vm_info['vm_fqdn'], recursive=True)
        print "   - Delete zookeeper puppet node"
        deleteZookeeperPath(zk_base_path + '/' + vm_info['puppet_environment'] + '/nodes/' + vm_info['vm_fqdn'], recursive=True)
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
