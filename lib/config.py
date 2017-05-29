#!/usr/bin/python
import os
import sys
import ConfigParser

class Config:
    def __init__(self, conf_file):
        self.salt = 'ConclusionCore'
        self.conf_file = conf_file
        self.vm_list = {}
        self.supported_hypervisors = ['vmware', 'ovirt', 'rhev']
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
                try:
                    self.zookeeper_address = self.config.get(section, 'zookeeper_address')
                except:
                    print 'No zookeeper server defined. Cannot continue'
                    sys.exit(99)
                try:
                    self.zookeeper_port = self.config.get(section, 'zookeeper_port')
                except:
                    print 'No zookeeper port defined. Assuming default of 2181'
                    self.zookeeper_port = '2181'
                try:
                    self.puppetmaster_address = self.config.get(section, 'puppetmaster_address')
                except:
                    print 'No puppetmaster server defined. Cannot continue'
                    sys.exit(99)
                try:
                    self.puppetmaster_port = self.config.get(section, 'puppetmaster_port')
                except:
                    print 'No puppetmaster port defined. Assuming default of 8140'
                    self.puppetmaster_port = '8140'
                try:
                    self.freeipa_address = self.config.get(section, 'freeipa_address')
                except:
                    print "No freeipa server defined. Will continue but cannot register the host in any additional hostgroups"
                    self.freeipa_address = ''
                    self.freeipa_user = ''
                    self.freeipa_password = ''
                if self.freeipa_address != '':
                    try:
                        self.freeipa_user = self.config.get(section, 'freeipa_user')
                    except:
                        print "No freeipa user specified. Will continue but cannot register the host in any additional hostgroups"
                        self.freeipa_user = ''
                    try:
                        self.freeipa_password = self.config.get(section, 'freeipa_password')
                    except:
                        print "No freeipa password specified. Will continue but cannot register the host in any additional hostgroups"
                        self.freeipa_password = ''
                try:
                    self.vm_type = self.config.get(section, 'vm_type')
                except:
                    print "No vm_type defined. Asuming 'other'"
                    self.vm_type = 'other'
                if self.vm_type.lower() == 'oracle-rac':
                    try:
                        self.shared_disks = self.config.get(section, 'shared_disks').split(',')
                        self.shared_disks = [disk.strip() for disk in self.shared_disks]
                    except:
                        print "No shared disks specified for vm_type oracle-rac. Cannot continue"
                        sys.exit(99)
                try:
                    self.use_fqdn_as_name = int(self.config.get(section, 'use_fqdn_as_name'))
                except:
                    self.use_fqdn_as_name = 1
            else:
                vm_list[section] = {}
                try:
                    vm_list[section]['osfamily'] = self.config.get(section, 'osfamily').lower()
                except:
                    print "No osfamily specified (linux or windows). Cannot continue"
                    sys.exit(99)
                try:
                    vm_list[section]['vm_domain'] = self.config.get(section, 'vm_domain').lower()
                except:
                    print "No domain provided."
                    vm_list[section]['vm_domain'] = ''
                try:
                    vm_list[section]['vm_exists'] = int(self.config.get(section, 'vm_exists'))
                except:
                    vm_list[section]['vm_exists'] = 0
                if vm_list[section]['vm_domain'] == '':
                    vm_list[section]['vm_fqdn'] = section.lower()
                else:
                   vm_list[section]['vm_fqdn'] = section.lower() + '.' + vm_list[section]['vm_domain']
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
                    vm_list[section]['hypervisor_type'] = self.config.get(section, 'hypervisor_type')
                except:
                    print "No hypervisor type provided. Cannot continue"
                    sys.exit(99)
                if vm_list[section]['hypervisor_type'].lower() not in self.supported_hypervisors:
                    print "Unsupported hypervisor '%s'. Cannot continue" % vm_list[section]['hypervisor_type']
                    sys.exit(99)
                if vm_list[section]['hypervisor_type'].lower() == 'vmware':
                    try:
                        vm_list[section]['vm_datacenter'] = self.config.get(section, 'vm_datacenter')
                    except:
                        print "No datacenter provided. Cannot continue"
                        sys.exit(99)
                    try:
                        vm_list[section]['vm_datacenter_folder'] = self.config.get(section, 'vm_datacenter_folder')
                    except:
                        print "No datacenter folder provided. Assuming root folder of datacenter"
                        vm_list[section]['vm_datacenter_folder'] = ''
                    try:
                        vm_list[section]['hypervisor_host'] = self.config.get(section, 'hypervisor_host')
                    except:
                        print "No hypervisor host provided. Cannot continue"
                        sys.exit(99)
                    try:
                        vm_list[section]['hypervisor_version'] = self.config.get(section, 'hypervisor_version')
                    except:
                        print "No vmware-hypervisor version provided. Assuming version 8"
                        vm_list[section]['hypervisor_version'] = 'vmx-08'
                    try:
                        vm_list[section]['vm_os'] = self.config.get(section, 'vm_os')
                    except:
                        print "No vm_os provided. Leaving option blank"
                        vm_list[section]['vm_os'] = ''
                    try:
                        vm_list[section]['vm_iso'] = self.config.get(section, 'vm_iso')
                    except:
                        print "No vm_iso provided. Leaving option blank"
                        vm_list[section]['vm_iso'] = ''
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
                    vm_list[section]['vm_cores_per_cpu'] = self.config.get(section, 'vm_cores_per_cpu')
                except:
                    print "No number of cores per cpu's provided. Assuming default of 1"
                    vm_list[section]['vm_cores_per_cpu'] = 1
                try:
                    vm_list[section]['vm_disks'] = self.config.get(section, 'vm_disks').split(',')
                    vm_list[section]['vm_disks'] = [disk.strip() for disk in vm_list[section]['vm_disks']]
                except:
                    print "No disks provided. Assuming single disk of 16 GB"
                    vm_list[section]['vm_disks'] = ['16']
                try:
                    vm_list[section]['vm_purpose'] = self.config.get(section, 'vm_purpose')
                except:
                    vm_list[section]['vm_purpose'] = ''
                try:
                    vm_list[section]['vm_networks'] = self.config.get(section, 'vm_networks').split(',')
                    vm_list[section]['vm_networks'] = [network.strip() for network in vm_list[section]['vm_networks']]
                except:
                    print "No VLAN provided. You can still access the VM, but only through the console."
                    vm_list[section]['vm_networks'] = []
                try:
                    vm_list[section]['vm_network_type'] = self.config.get(section, 'vm_network_type').lower()
                except:
                    print "No network_type provided. Assuming 'standard' (NOT distributed v-switch)"
                    vm_list[section]['vm_network_type'] = 'standard'
                try:
                    vm_list[section]['vm_macaddress'] = self.config.get(section, 'vm_macaddress')
                except:
                    if vm_list[section]['vm_exists'] == 1:
                        print "No MAC address provided but the VM does allready exist. I don't know what to do"
                        sys.exit(99)
                    else:
                        vm_list[section]['vm_macaddress'] = ''
                try:
                    vm_list[section]['vm_ipaddress'] = self.config.get(section, 'vm_ipaddress')
                except:
                    if vm_list[section]['osfamily'] == 'windows':
                        print "No ipaddress specified. Windows provisioning currently needs an IP address. Cannot continue"
                        sys.exit(99)
                    else:
                        vm_list[section]['vm_ipaddress'] = ''
                try:
                    vm_list[section]['snapshot_to_restore'] = self.config.get(section, 'snapshot_to_restore')
                    vm_list[section]['can_restore'] = True
                except:
                    vm_list[section]['can_restore'] = False
                try:
                    vm_list[section]['boot_after_restore'] = self.config.get(section, 'boot_after_restore')
                except:
                    print 'Boot after restore not specified. Assuming NO (this will only be used when reverting to a snapshot)'
                    vm_list[section]['boot_after_restore'] = '0'
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
                    vm_list[section]['startup_after_creation'] = int(self.config.get(section, 'startup_after_creation'))
                except:
                    print "No startup_after_creation provided. Assuming NO"
                    vm_list[section]['startup_after_creation'] = 0
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
                try:
                    vm_list[section]['ipa_hostgroup'] = self.config.get(section, 'ipa_hostgroup')
                except:
                    print "No IPA hostgroup specified. Not adding host to any hostgroup"
                    vm_list[section]['ipa_hostgroup'] = ''
                try:
                    import ast
                    vm_list[section]['override_parameters'] = ast.literal_eval(self.config.get(section, 'override_parameters'))
                except:
                    vm_list[section]['override_parameters'] = []
                try:
                     vm_list[section]['ossec_in_env'] = int(self.config.get(section, 'ossec_in_env'))
                except:
                    vm_list[section]['ossec_in_env'] = 1
                try:
                    vm_list[section]['deploy_via_wds'] = int(self.config.get(section, 'deploy_via_wds'))
                except:
                    vm_list[section]['deploy_via_wds'] = 0

                self.vm_list = vm_list


