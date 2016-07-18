#! /usr/bin/python

# Created by Jens Depuydt
# http://www.jensd.be
# http://github.com/jensdepuydt

#this script requires ovirt-engine-sdk-python

from ovirtsdk.api import API
from ovirtsdk.xml import params
from time import sleep

def connectToHost(host,host_user,host_pw):
    apiurl="https://"+host+"/api"
    #insecure -> skips SSL check
    api = API(url=apiurl,username=host_user,password=host_pw,insecure=True)
    return api

def createGuest(api,guest_cluster,guest_name,guest_description,guest_mem,guest_cpu,guest_disks_gb,guest_domain,guest_networks):
    cpu_params = params.CPU(topology=params.CpuTopology(cores=guest_cpu))
    try:
        api.vms.add(params.VM(name=guest_name,memory=guest_mem*1024*1024,cluster=api.clusters.get(guest_cluster),template=api.templates.get('Blank'),cpu=cpu_params,type_="server",description=guest_description))

        for ethnum in range(len(guest_networks)):
            api.vms.get(guest_name).nics.add(params.NIC(name='eth'+str(ethnum), network=params.Network(name=guest_networks[ethnum]), interface='virtio'))

        #create bootdisk. First disk is allways bootdisk
        api.vms.get(guest_name).disks.add(params.Disk(storage_domains=params.StorageDomains(storage_domain=[api.storagedomains.get(guest_domain)]),size=int(guest_disks_gb[0])*1024*1024*1024,status=None,interface='virtio',format='cow',sparse=True,bootable=True))
        #create remaining disks
        if len(guest_disks_gb) > 1:
            for guest_disk_gb in guest_disks_gb[1:]:
                api.vms.get(guest_name).disks.add(params.Disk(storage_domains=params.StorageDomains(storage_domain=[api.storagedomains.get(guest_domain)]),size=int(guest_disk_gb)*1024*1024*1024,status=None,interface='virtio',format='cow',sparse=True,bootable=False))
        while api.vms.get(guest_name).status.state != 'down':
            sleep(1)

        #Wait for boot disk to be created
        disk_name=guest_name+"_Disk1"
        print "Waiting for "+disk_name+" to reach ok status"
        while api.vms.get(guest_name).disks.get(name=disk_name).status.state != 'ok':
            sleep(1)
        result = "Succesfully created guest: " + guest_name
    except Exception as e:
        result = 'Failed to create VM with disk and NIC: %s' % str(e)

    return result

def getMac(api,guest_name):
    return api.vms.get(guest_name).nics.get("eth0").mac.address

def setPXEBoot(api, guest_name):
    vm = api.vms.get(name=guest_name)
    hd_boot_dev = params.Boot(dev='hd')
    net_boot_dev = params.Boot(dev='network')
    vm.os.set_boot([hd_boot_dev, net_boot_dev])
    vm.update()

def powerOnGuest(api,guest_name):
    try:
        if api.vms.get(guest_name).status.state != 'up':
            print 'Starting VM: %s' % guest_name
            api.vms.get(guest_name).start()
            print 'Waiting for VM to reach Up status'
            while api.vms.get(guest_name).status.state != 'up':
                sleep(1)
        else:
            print 'VM already up'
    except Exception as e:
        print 'Failed to Start VM: %s\n%s' % (guest_name, str(e))

def powerOffGuest(api,guest_name):
    try:
        if api.vms.get(guest_name).status.state != 'down':
            print 'Stopping VM: %s' % guest_name
            api.vms.get(guest_name).stop()
            print 'Waiting for VM to reach Down status'
            while api.vms.get(guest_name).status.state != 'down':
                sleep(1)
        else:
            print 'VM already down'
    except Exception as e:
        print 'Failed to Stop VM: %s\n%s' % (guest_name, str(e))

def revertToSnapshot(api, guest_name, snapshot_name, boot_after_restore):
    guest_snapshots = api.vms.get(guest_name).snapshots.list()
    try:
        for snapshot in guest_snapshots:
            if snapshot.get_description() == snapshot_name:
                print "Snapshot %s found" % snapshot_name
                powerOffGuest(api, guest_name)
                print "Restoring snapshot"
                snapshot.restore()
                print "Reactivating NIC(s)"
                guest_nics = api.vms.get(guest_name).nics.list()
                for nic in guest_nics:
                    nic.activate()
                if boot_after_restore == '1':
                    powerOnGuest(api, guest_name)
    except Exception as e:
        print "Failed to revert snapshot '%s' on VM: %s\n%s" % (snapshot_name, guest_name, str(e))

def destroyGuest(api, guest_name):
    powerOffGuest(api, guest_name)
    try:
        api.vms.get(guest_name).delete()
        print 'Waiting for VM to be deleted'
        while guest_name in [vm.name for vm in api.vms.list()]:
            sleep(1)
        result = 'Succesfully removed guest: %s' % guest_name
    except Exception as e:
        result = 'Failed to remove VM: %s\n%s' % (guest_name, str(e))
    return result
