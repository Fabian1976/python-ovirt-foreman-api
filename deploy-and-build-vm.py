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
import collections #to order dict by key

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/lib')
import api_ovirt
import api_vmware
import api_foreman
import api_zookeeper
import api_freeipa
import kazoo.exceptions

vm_config = None
zk_base_path = '/puppet'
wds_mount = '/mnt/dsc'

from config import Config
import simplecrypt
import base64
#disable warnings urllib
import warnings
warnings.simplefilter('ignore')
#disable warnings Foreman API
import logging
logging.disable(logging.ERROR)
#needed to generate key for ossec
import hashlib

def prerequisites():
    #Check if DSC share is mounted
#    if not os.path.ismount(wds_mount):
#        print "DSC share not mounted. Cannot continue"
#        sys.exit(99)
    #Check if puppetmaster is reachable
    #Check if Foreman is reachable
    #Check if hypervisor is reachable
    #Check if Zookeeper is reachable
    #Check if IPA is reachable
    pass

def create_ossec_key(zookeeper_conn, hostname, puppet_environment, ip_address):
    agent_seed = 'xaeS7ahf'
    ossecserver, nodeStats = api_zookeeper.getValue(zookeeper_conn, zk_base_path + '/production/defaults/core::profile::ossec::client::ossec_server')
    ossecserver_path = zk_base_path + '/production/nodes/' + ossecserver
    try:
        agent_id, nodeStats = api_zookeeper.getValue(zookeeper_conn, ossecserver_path + '/client-keys/' + hostname + '/id')
        print "Host reeds bekend in OSSec"
    except kazoo.exceptions.NoNodeError:
        print "   - Fetching moest recent ossec client-num"
        agent_id, nodeStats = api_zookeeper.getValue(zookeeper_conn, ossecserver_path + '/client-num')
        agent_id = int(agent_id)
        print "     - %s" % agent_id
        agent_id += 1
        print "   - Generating OSsec key"
        agent_key1 = hashlib.md5(str(agent_id) + ' ' + agent_seed).hexdigest()
        agent_key2 = hashlib.md5(hostname + ' ' + ip_address + ' ' + agent_seed).hexdigest()
        agent_key = agent_key1 + agent_key2
        print "   - Storing values for OSsec-server"
        print "     - %s" % api_zookeeper.storeValue(zookeeper_conn, ossecserver_path + '/client-num', str(agent_id))
        print "     - %s" % api_zookeeper.storeValue(zookeeper_conn, ossecserver_path + '/client-keys/' + hostname + '/id', str(agent_id))
        print "     - %s" % api_zookeeper.storeValue(zookeeper_conn, ossecserver_path + '/client-keys/' + hostname + '/ip', ip_address)
        print "     - %s" % api_zookeeper.storeValue(zookeeper_conn, ossecserver_path + '/client-keys/' + hostname + '/key', agent_key)
        print "   - Storing values for OSsec-client"
        zk_path = zk_base_path + '/' + puppet_environment + '/nodes/' + hostname
        print "     - %s" % api_zookeeper.storeValue(zookeeper_conn, zk_path + '/ossec::client::ossec_client_id', str(agent_id))
        print "     - %s" % api_zookeeper.storeValue(zookeeper_conn, zk_path + '/ossec::client::ossec_client_ip', ip_address)
        print "     - %s" % api_zookeeper.storeValue(zookeeper_conn, zk_path + '/ossec::client::ossec_client_key', agent_key)

def store_provisioning(zookeeper_conn):
    for vm in vm_config.vm_list:
        vm_info = vm_config.vm_list[vm]
        api_zookeeper.storeValue(zookeeper_conn, '/provisioning/%s/%s/%s/RequestInfo/Infra/OS' % (vm_info['vm_domain'], vm_info['puppet_environment'], vm_info['vm_fqdn']), vm_info['osfamily'])
        if len(vm_info['vm_disks']) > 1:
            disknum = 1
            for disk in vm_info['vm_disks']:
                api_zookeeper.storeValue(zookeeper_conn, '/provisioning/%s/%s/%s/RequestInfo/Infra/disk/%s' % (vm_info['vm_domain'], vm_info['puppet_environment'], vm_info['vm_fqdn'], disknum), disk)
                disknum += 1
        else:
            api_zookeeper.storeValue(zookeeper_conn, '/provisioning/%s/%s/%s/RequestInfo/Infra/disk' % (vm_info['vm_domain'], vm_info['puppet_environment'], vm_info['vm_fqdn']), vm_info['vm_disks'][0])
        api_zookeeper.storeValue(zookeeper_conn, '/provisioning/%s/%s/%s/RequestInfo/Infra/mem' % (vm_info['vm_domain'], vm_info['puppet_environment'], vm_info['vm_fqdn']), vm_info['vm_memory'])
        if len(vm_info['vm_networks']) > 1:
            networknum = 1
            for network in vm_info['vm_networks']:
                api_zookeeper.storeValue(zookeeper_conn, '/provisioning/%s/%s/%s/RequestInfo/Infra/network/%s' % (vm_info['vm_domain'], vm_info['puppet_environment'], vm_info['vm_fqdn'], networknum), network)
                networknum += 1
        else:
            api_zookeeper.storeValue(zookeeper_conn, '/provisioning/%s/%s/%s/RequestInfo/Infra/network' % (vm_info['vm_domain'], vm_info['puppet_environment'], vm_info['vm_fqdn']), vm_info['vm_networks'][0])
        api_zookeeper.storeValue(zookeeper_conn, '/provisioning/%s/%s/%s/DateInitialRequest' % (vm_info['vm_domain'], vm_info['puppet_environment'], vm_info['vm_fqdn']), time.strftime("%d-%m-%Y %H:%M:%S"))
        api_zookeeper.storeValue(zookeeper_conn, '/provisioning/%s/%s/%s/RequestInfo/CnfgMnmgmt/roles' % (vm_info['vm_domain'], vm_info['puppet_environment'], vm_info['vm_fqdn']), vm_info['puppet_server_role'])

def createVMs():
    for vm in sorted(vm_config.vm_list.keys()):
        vm_info = vm_config.vm_list[vm]

        if vm_info['vm_exists'] == 0:
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

            print " - Create VM on hypervisor"
            print "   - hypervisor:", vm_info["hypervisor"]
            print "   - hypervisor type:", vm_info['hypervisor_type']
            print "   - datastore:", vm_info["vm_datastore"]
            print "   - name:", vm_name
            print "   - domain:", vm_info['vm_domain']
            print "   - #cpu:", vm_info["vm_cpus"]
            print "   - #cores per cpu:", vm_info['vm_cores_per_cpu']
            print "   - memory:", vm_info["vm_memory"],"MB"
            print "   - disks:"
            for disk in vm_info["vm_disks"]:
                print "     - " + disk + "GB"
            print "   - vlans:"
            for network in vm_info['vm_networks']:
                print "     - " + network
            print ""

            if vm_info['hypervisor_type'].lower() in ['ovirt', 'rhev']:
                result = api_ovirt.createGuest(hypervisor_conn, vm_info["vm_cluster"], vm_name, vm_info["vm_purpose"], int(vm_info["vm_memory"]), int(vm_info["vm_cpus"]), vm_info["vm_disks"], vm_info["vm_datastore"], vm_info["vm_networks"])
            else:
                result = api_vmware.createGuest(hypervisor_conn, vm_info['vm_datacenter'], vm_info['vm_datacenter_folder'], vm_info['hypervisor_host'], vm_name, vm_info['hypervisor_version'], int(vm_info["vm_memory"]), int(vm_info["vm_cpus"]), int(vm_info['vm_cores_per_cpu']), vm_info["vm_purpose"], vm_info['vm_iso'], vm_info['vm_os'], vm_info['vm_disks'], vm_info["vm_datastore"], vm_info['vm_networks'], vm_info['vm_network_type'])
            if result != "Succesfully created guest: " + vm_name:
                print result
                print "Finished unsuccesfully, aborting"
                hypervisor_conn.disconnect()
                sys.exit(99)
            print " -", result

            print " - Retrieve MAC address to pass to foreman"
            if vm_info['hypervisor_type'].lower() in ['ovirt', 'rhev']:
                vm_info['vm_macaddress'] = api_ovirt.getMac(hypervisor_conn, vm_name)
                print "   - Found MAC: %s" % vm_info['vm_macaddress']
            else:
                vm_info['vm_macaddress'] = api_vmware.getMac(hypervisor_conn, vm_name)
                for macaddress in vm_info['vm_macaddress']:
                   print "   - Found MAC: %s" % macaddress
        else:
            print " - Using MAC address: %s" % vm_info['vm_macaddress']
        if vm_info['osfamily'] == 'linux':
            print " - Connect to Foreman"
            foreman_conn = api_foreman.connectToHost(vm_info["foreman"], vm_info["foreman_user"], simplecrypt.decrypt(vm_config.salt, base64.b64decode(vm_info['foreman_password'])))
            print "   - Create host in foreman"
            print "     - foreman:", vm_info['foreman']
            print "     - hostgroup:", vm_info['foreman_hostgroup']
            print "     - organization:", vm_info['foreman_organization']
            print "     - location:", vm_info['foreman_location']
            print "     - subnet:", vm_info['foreman_subnet']
            if vm_info['vm_ipaddress']:
                print "     - ipaddress:", vm_info['vm_ipaddress']
            print "     - puppet environment:", vm_info['puppet_environment']
            if vm_info['vm_ipaddress']:
                result = api_foreman.createGuest(foreman_conn, vm, vm_info['foreman_hostgroup'], vm_info['vm_domain'], vm_info['foreman_organization'], vm_info['foreman_location'], vm_info['vm_macaddress'], vm_info['foreman_subnet'], vm_info['puppet_environment'], vm_info['foreman_ptable'], 'true', vm_info['vm_ipaddress'])
            else:
                result = api_foreman.createGuest(foreman_conn, vm, vm_info['foreman_hostgroup'], vm_info['vm_domain'], vm_info['foreman_organization'], vm_info['foreman_location'], vm_info['vm_macaddress'], vm_info['foreman_subnet'], vm_info['puppet_environment'], vm_info['foreman_ptable'], 'true')
            if result != "Succesfully created guest: " + vm:
                print result
                print "Finished unsuccesfully, aborting"
                sys.exit(99)
            print "   -", result
            print "   - Fetching IP address to generate OSSec key"
            ip_address = api_foreman.getHostIP(foreman_conn, vm)
            print "     - IP-address: %s" % ip_address
            print ""
            print " - Connect to zookeeper"
            zookeeper_conn = api_zookeeper.connectToHost(vm_config.zookeeper_address, vm_config.zookeeper_port)
            if vm_info['ossec_in_env'] == 1:
                create_ossec_key(zookeeper_conn, vm_info['vm_fqdn'], vm_info['puppet_environment'], ip_address)

            if vm_info['puppet_server_role'] != '':
                print " - Creating role in Zookeeper"
                print "   - server role:", vm_info['puppet_server_role']
                zk_path = zk_base_path + '/' + vm_info['puppet_environment'] + '/nodes/' + vm_info['vm_fqdn'] + '/roles'
                result = api_zookeeper.storeValue(zookeeper_conn, zk_path, vm_info['puppet_server_role'])
                if result != "Succesfully stored value '%s' at path '%s'" % (vm_info['puppet_server_role'], zk_path):
                    print result
                    print "Finished unsuccesfully, aborting"
                    sys.exit(99)
                print '   -', result
            print "   - Storing provisioning info"
            store_provisioning(zookeeper_conn)
            print " - Disconnect from zookeeper"
            api_zookeeper.disconnect(zookeeper_conn)
            if vm_config.freeipa_address != '' and vm_config.freeipa_user != '' and vm_config.freeipa_password != '' and vm_info['ipa_hostgroup'] != '':
                print " - Connect to freeipa server"
                freeipa_conn = api_freeipa.connectToHost(vm_config.freeipa_address, vm_config.freeipa_user, simplecrypt.decrypt(vm_config.salt, base64.b64decode(vm_config.freeipa_password)))
                print "   - Registering host '%s' with hostgroup '%s'" % (vm_info['vm_fqdn'], vm_info['ipa_hostgroup'])
                api_freeipa.add_host_hostgroup(freeipa_conn, vm_info['ipa_hostgroup'], vm_info['vm_fqdn'])
            if vm_info['deploy_via_wds']:
                print " - Writing file for WDS to pickup and create DHCP reservation."
                write_wds_file(vm, vm_info)
                print " - Waiting for .done file to appear when WDS is done"
                while not os.path.exists(wds_mount + '/' + vm + '.done'):
                    time.sleep(5)
                    print "   - %s/%s.done' still not there" % (wds_mount, vm)
        if vm_info['vm_exists'] == 1:
            #exit gracefully if VM allready exists. When VM allready exists, the names don't match (detached mode) and below functions don't work
            sys.exit(0)
    print " - Disconnect from hypervisor"
    hypervisor_conn.disconnect()
    #set PXEboot for hosts
    if vm_info['hypervisor_type'].lower() in ['ovirt', 'rhev']:
        for vm in vm_config.vm_list:
            #determine how VM is named
            if vm_config.use_fqdn_as_name == 0:
                vm_name = vm
            else:
                vm_name = vm_info['vm_fqdn']

            vm_info = vm_config.vm_list[vm]
            hypervisor_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], simplecrypt.decrypt(vm_config.salt, base64.b64decode(vm_info['hypervisor_password'])))
            api_ovirt.setPXEBootSecond(hypervisor_conn, vm_name)
    hypervisor_conn.disconnect()

    #create shareable disks if vm_type = oracle-rac
    if vm_config.vm_type.lower() == 'oracle-rac':
        print "\n - Creating shareable disks. These are thick-provisioned so it can take a while"
        disk_counter = 1
        for vm in sorted(vm_config.vm_list.keys()):
            vm_info = vm_config.vm_list[vm]
            #determine how VM is named
            if vm_config.use_fqdn_as_name == 0:
                vm_name = vm
            else:
                vm_name = vm_info['vm_fqdn']

            if vm_info['hypervisor_type'].lower() in ['ovirt', 'rhev']:
                hypervisor_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], simplecrypt.decrypt(vm_config.salt, base64.b64decode(vm_info['hypervisor_password'])))
                for disk in vm_config.shared_disks:
                    api_ovirt.createDisk(hypervisor_conn, vm_name, vm_info['vm_datastore'], disk, disk_format='raw', thin_provision=False, shareable=True, disk_name=vm_name+'_racdisk'+str(disk_counter).zfill(2))
                    disk_counter += 1
            host_disks = vm_name
            break #Disk only need to be created on the first VM. So break the loop
        #attach shareable disks to other hosts
        for vm in vm_config.vm_list:
            vm_info = vm_config.vm_list[vm]
            #determine how VM is named
            if vm_config.use_fqdn_as_name == 0:
                vm_name = vm
            else:
                vm_name = vm_info['vm_fqdn']

            if vm_name != host_disks:
                disk_counter = 1
                for disk in vm_config.shared_disks:
                    api_ovirt.attachDisk(hypervisor_conn, vm_name, host_disks+'_racdisk'+str(disk_counter).zfill(2))
                    disk_counter += 1
        hypervisor_conn.disconnect()

    #start hosts
    for vm in vm_config.vm_list:
        vm_info = vm_config.vm_list[vm]
        #determine how VM is named
        if vm_config.use_fqdn_as_name == 0:
            vm_name = vm
        else:
            vm_name = vm_info['vm_fqdn']

        if vm_info['startup_after_creation']:
            if vm_info['hypervisor_type'].lower() in ['ovirt', 'rhev']:
                hypervisor_conn = api_ovirt.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], simplecrypt.decrypt(vm_config.salt, base64.b64decode(vm_info['hypervisor_password'])))
                if vm_info['override_parameters']:
                    print " - Additional parameters provided. This may take a while"
                    api_foreman.createParameters(foreman_conn, vm_info['vm_fqdn'], vm_info['override_parameters'])
                print " - Starting VM %s" % vm_name
                api_ovirt.powerOnGuest(hypervisor_conn, vm_name)
            else:
                hypervisor_conn = api_vmware.connectToHost(vm_info["hypervisor"], vm_info["hypervisor_user"], simplecrypt.decrypt(vm_config.salt, base64.b64decode(vm_info['hypervisor_password'])))
                if vm_info['override_parameters']:
                    print " - Additional parameters provided. This may take a while"
                    api_foreman.createParameters(foreman_conn, vm_info['vm_fqdn'], vm_info['override_parameters'])
                print " - Starting VM %s" % vm_name
                api_ovirt.powerOnGuest(hypervisor_conn, vm_name)
            hypervisor_conn.disconnect()

def write_wds_file(vm, vm_info):
    print " - Writing file to WDS pickup location"
    print "   - domain      = %s" % vm_info['vm_domain']
    print "   - os          = %s" % vm_info['osfamily']
    print "   - ip          = %s" % vm_info['vm_ipaddress']
    print "   - mac         = %s" % vm_info['vm_macaddress']
    print "   - bootserver  = %s" % '10.128.96.49'
    print "   - environment = %s" % vm_info['puppet_environment']
    f = open(wds_mount + '/' + vm + '.start', "w")
    f.write("domain      = %s\r\n" % vm_info['vm_domain'])
    f.write("os          = %s\r\n" % vm_info['osfamily'])
    f.write("ip          = %s\r\n" % vm_info['vm_ipaddress'])
    f.write("mac         = %s\r\n" % vm_info['vm_macaddress'])
    f.write("bootserver  = %s\r\n" % '10.128.96.49')
    f.write("environment = %s\r\n" % vm_info['puppet_environment'])
    f.close()

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
    prerequisites()
    print "These VM's will be created:"
    for vm in sorted(vm_config.vm_list.keys()):
        print '- ' + vm
        for key, value in collections.OrderedDict(sorted(vm_config.vm_list[vm].items())).items():
            if not isinstance(value, list):
                print '\t- %s: %s' % (key, value)
            else:
                print '\t- %s:' % key
                for v in value:
                    print '\t\t- %s' % v
    if vm_config.vm_type.lower() == 'oracle-rac':
        print "\nVM type = %s" % vm_config.vm_type
        print "Shared disks to be created in this order:"
        for disk in vm_config.shared_disks:
            print '\t- %s GB' % disk
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
