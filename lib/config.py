#!/usr/bin/python
import os
import ConfigParser

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
            else:
                vm_list[section] = {}
                try:
                    vm_list[section]['osfamily'] = self.config.get(section, 'osfamily').lower()
                except:
                    print "No osfamily specified (linux or windows). Cannot continue"
                    sys.exit(99)
                try:
                    vm_list[section]['vm_domain'] = self.config.get(section, 'vm_domain')
                except:
                    print "No domain provided."
                    vm_list[section]['vm_domain'] = ''
                if vm_list[section]['vm_domain'] == '':
                    vm_list[section]['vm_fqdn'] = section
                else:
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
                    vm_list[section]['vm_ipaddress'] = self.config.get(section, 'vm_ipaddress')
                except:
                    if vm_list[section]['osfamily'] == 'windows':
                        print "No ipaddress specified. Windows provisioning currently needs an IP address. Cannot continue"
                        sys.exit(99)
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
                self.vm_list = vm_list

