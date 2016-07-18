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
from kazoo.client import KazooClient #Zookeeper client class
import kazoo #Zookeeper class
import ConfigParser
import collections #to order dict by key

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/lib')
import api_ovirt
import api_foreman

vm_config = None
zk_base_path = '/puppet'
from config import Config

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
        print "   - vlans:"
        for network in vm_info['vm_networks']:
            print "     - " + network
        print ""
        result = api_ovirt.createGuest(ovirt_conn, vm_info["vm_cluster"], vm_info['vm_fqdn'], vm_info["vm_purpose"], int(vm_info["vm_memory"]), int(vm_info["vm_cpus"]), vm_info["vm_disks"], vm_info["vm_datastore"], vm_info["vm_networks"])
        if result != "Succesfully created guest: " + vm_info['vm_fqdn']:
            print result
            print "Finished unsuccesfully, aborting"
            ovirt_conn.disconnect()
            sys.exit(99)
        print " -", result

        print " - Retrieve MAC address to pass to foreman"
        vm_mac = api_ovirt.getMac(ovirt_conn, vm_info['vm_fqdn'])
        print "   - Found MAC: %s" % vm_mac
        if vm_info['osfamily'] == 'linux':
            print " - Connect to Foreman"
            foreman_conn = api_foreman.connectToHost(vm_info["foreman"], vm_info["foreman_user"], vm_info['foreman_password'])
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
            if vm_info['puppet_server_role'] != '':
                print " - Creating role in Zookeeper"
                print "   - server role:", vm_info['puppet_server_role']
                createRoleZookeeper(vm_info['vm_fqdn'], vm_info['puppet_environment'], vm_info['puppet_server_role'])
        elif vm_info['osfamily'] == 'windows':
            print " - Writing file to WDS pickup location"
            print "   - $Hostname = '%s'" % vm
            print "   - $vDC = '%s'" % vm.split('-')[0]
            print "   - $MAC = '%s'" % vm_mac
            print "   - $IP = '%s'" % vm_info['vm_ipaddress']
            print "   - $Role = '%s'" % vm_info['puppet_server_role'].upper()
            print "   - $OTAP = 'P'"
            print "   - $PuppetAgent_Arguments = 'PUPPET_MASTER_SERVER=puppetmaster01.core.cmc.lan PUPPET_AGENT_ENVIRONMENT=%s'" % vm_info["puppet_environment"]
            f = open('/mnt/dsc/' + vm + '.start', "w")
#            f = open('./' + vm + '.start', "w")
            f.write("$Hostname = '%s'\r\n" % vm)
            f.write("$vDC = '%s'\r\n" % vm.split('-')[0])
            f.write("$MAC = '%s'\r\n" % vm_mac)
            f.write("$IP = '%s'\r\n" % vm_info['vm_ipaddress'])
            f.write("$Role = '%s'\r\n" % vm_info['puppet_server_role'].upper())
            f.write("$OTAP = 'P'\r\n")
            f.write("$PuppetAgent_Arguments = 'PUPPET_MASTER_SERVER=puppetmaster01.core.cmc.lan PUPPET_AGENT_ENVIRONMENT=%s'\r\n" % vm_info["puppet_environment"])
            f.close()
            print " - Waiting for .done file to appear when WDS is done"
            while not os.path.exists('/mnt/dsc/' + vm + '.done'):
                time.sleep(2)
                print "   - '/mnt/dsc/%s.done' still not there" % vm
    print " - Disconnect from hypervisor"
    ovirt_conn.disconnect()
    #set PXEboot for hosts
    for vm in vm_config.vm_list:
        vm_info = vm_config.vm_list[vm]
        ovirt_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], vm_info['hypervisor_password'])
        api_ovirt.setPXEBoot(ovirt_conn, vm_info['vm_fqdn'])
    ovirt_conn.disconnect()
    #start hosts
    for vm in vm_config.vm_list:
        vm_info = vm_config.vm_list[vm]
        ovirt_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], vm_info['hypervisor_password'])
        print " - Starting VM %s" % vm_info['vm_fqdn']
        api_ovirt.powerOnGuest(ovirt_conn, vm_info['vm_fqdn'])
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
    if vm_config.unattended == '0':
        print "Is this correct? (y/n)"
        answer = raw_input().lower()
    else:
        answer = 'y'
    if answer == 'y':
        os.system('clear')
        createVMs()
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
