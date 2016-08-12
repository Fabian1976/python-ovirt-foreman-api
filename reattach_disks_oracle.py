#! /usr/bin/python

from ovirtsdk.api import API
from ovirtsdk.xml import params
from time import sleep

ovirt_host = 'poc-ovirtm1.infoplus-ot.ris'
#guest_name = 'puppetdev-remy01.core.cmc.lan'
#attach_to = 'puppetdev-remy02.core.cmc.lan'
guest_name = 'puppetdev-johnpaul01.core.cmc.lan'
attach_to = 'puppetdev-johnpaul02.core.cmc.lan'
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
disk['size'] = '4'
disks['systemdg_001'] = disk
disks['systemdg_002'] = disk
disks['systemdg_003'] = disk
disks['systemdg_004'] = disk
disk = None

apiurl = "https://" + ovirt_host + "/api"
api = API(url=apiurl,username='admin@internal',password='redhat',insecure=True)

print "Reattaching disks to VM: %s" % guest_name
for disk in disks:
    print "Attaching disk '%s' to: %s" % (disk, guest_name)
    api.vms.get(guest_name).disks.add(params.Disk(id=api.disks.get(alias=guest_name+'_'+disk).id, active=True))
    print "Attaching disk '%s' to: %s" % (disk, attach_to)
    api.vms.get(attach_to).disks.add(params.Disk(id=api.disks.get(alias=guest_name+'_'+disk).id, active=True))
