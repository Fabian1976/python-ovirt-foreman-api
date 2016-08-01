#! /usr/bin/python

from ovirtsdk.api import API
from ovirtsdk.xml import params
from time import sleep

ovirt_host = 'poc-ovirtm1.infoplus-ot.ris'
guest_name = 'puppetdev-remy01.core.cmc.lan'
attach_to = 'puppetdev-remy02.core.cmc.lan'
datastore = 'poc-datastore1'

disks = {}
disk = {}
disk['size'] = '1'
disks['backupdg_001'] = disk
disks['backupdg_002'] = disk
disk = {}
disk['size'] = '15'
disks['datadg_001'] = disk
disks['datadg_002'] = disk
disk = {}
disk['size'] = '6'
disks['recodg_001'] = disk
disks['recodg_002'] = disk
disk = {}
disk['size'] = '1'
disks['systemdg_001'] = disk
disks['systemdg_002'] = disk
disks['systemdg_003'] = disk
disks['systemdg_004'] = disk
disk = None

apiurl = "https://" + ovirt_host + "/api"
api = API(url=apiurl,username='admin@internal',password='redhat',insecure=True)

for disk in disks:
    print "Creating disk '%s' with size '%sGB'" % (disk, disks[disk]['size'])
    api.vms.get(guest_name).disks.add(params.Disk(storage_domains=params.StorageDomains(storage_domain=[api.storagedomains.get(datastore)]),size=int(disks[disk]['size'])*1024*1024*1024,status=None,interface='virtio',format='raw',sparse=False,bootable=False, shareable=True, alias=guest_name+'_'+disk))
    print "  - Waiting for disk to be fully allocated"
    while api.vms.get(guest_name).disks.get(name=guest_name+'_'+disk).status.state != 'ok':
        sleep(1)
    print "  - OK"
print "All disks created."
print "Activating disks"
for disk in disks:
    print "Activating: %s" % disk
    api.vms.get(guest_name).disks.get(name=guest_name+'_'+disk).activate()
print "Attaching disks to secondary VM: %s"
for disk in disks:
    print "Attaching disk '%s' to: %s" % (disk, attach_to)
    api.vms.get(attach_to).disks.add(params.Disk(id=api.disks.get(alias=guest_name+'_'+disk).id, active=True))
