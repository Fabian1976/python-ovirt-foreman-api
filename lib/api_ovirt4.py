#! /usr/bin/python

# Created by Fabian van der Hoeven
# https://github.com/Fabian1976

#this script requires ovirt-engine-sdk-python

import ovirtsdk4 as sdk
import ovirtsdk4.types as types
import time
import sys

def connectToHost(host, host_user, host_pw):
    apiurl = "https://"+host+"/ovirt-engine/api"
    #insecure -> skips SSL check
    connection = sdk.Connection(url = apiurl, username = host_user, password = host_pw, insecure = True)
    return connection

def createDisk(connection, vm_name, storage_domain, disk_size, disk_format = 'cow', thin_provision = True, bootable = False, shareable = False, disk_name = None):
    #By default this function creates a non-bootable, non-shareable, thin provisioned cow formatted disk with a default name
    vms_service = connection.system_service().vms_service()
    vm = vms_service.list(search = vm_name)[0]
    disk_attachments_service = vms_service.vm_service(vm.id).disk_attachments_service()
    disk_attachment = disk_attachments_service.add(
        types.DiskAttachment(
            disk = types.Disk(
                name = disk_name,
                description = disk_name,
                format = types.DiskFormat[disk_format.upper()],
                provisioned_size = int(disk_size) * 1024 * 1024 * 1024,
                storage_domains = [
                    types.StorageDomain(
                        name = storage_domain,
                    ),
                ],
                shareable = shareable,
                sparse = thin_provision,
            ),
            interface = types.DiskInterface.VIRTIO,
            bootable = bootable,
            active = True,
        ),
    )
    print "Waiting for disk %s to be created" % disk_name

    disks_service = connection.system_service().disks_service()
    disk_service = disks_service.disk_service(disk_attachment.disk.id)
    while disk_service.get().status != types.DiskStatus.OK:
        time.sleep(1)

def attachDisk(connection, vm_name, disk_name):
    print "Attaching disk '%s' to: %s" % (disk_name, vm_name)
    connection.vms.get(vm_name).disks.add(params.Disk(id=connection.disks.get(alias=disk_name).id, active=True))

def deleteDisk(connection, disk_name):
    print "Deleting disk %s" % disk_name
    connection.disks.list(alias=disk_name)[0].delete()

def createGuest(connection, guest_cluster, guest_name, guest_description, guest_mem, guest_cpu, guest_disks_gb, guest_domain, guest_networks):
    cpu_params = types.Cpu(
        topology = types.CpuTopology(
            cores = guest_cpu
        )
    )
    try:
        vms_service = connection.system_service().vms_service()
        vms_service.add(
            types.Vm(
                name = guest_name,
                memory = guest_mem*1024*1024,
                cluster = types.Cluster(
                    name = guest_cluster
                ),
                template = types.Template(
                    name = 'Blank'
                ),
                cpu = cpu_params,
                type = types.VmType.SERVER,
                description=guest_description
            )
        )
        vm = vms_service.list(search=guest_name)[0]
        nics_service = vms_service.vm_service(vm.id).nics_service()
        for ethnum in range(len(guest_networks)):
            profiles_service = connection.system_service().vnic_profiles_service()
            profile_id = None
            for profile in profiles_service.list():
                if profile.name == guest_networks[ethnum]:
                    profile_id = profile.id
                    break
            if not profile_id:
                print "VLAN %s not found. Exiting." % guest_networks[ethnum]
                sys.exit(99)
            nics_service.add(
                types.Nic(
                    name = 'eth' + str(ethnum),
                    vnic_profile = types.VnicProfile(
                        id = profile_id
                    ),
                    interface = types.NicInterface.VIRTIO
                )
            )

        #create bootdisk. First disk is allways bootdisk
        createDisk(connection, guest_name, guest_domain, guest_disks_gb[0], bootable = True, disk_name = guest_name + "_Disk1")
        #create remaining disks
        if len(guest_disks_gb) > 1:
            disk_num = 2
            for guest_disk_gb in guest_disks_gb[1:]:
                createDisk(connection, guest_name, guest_domain, guest_disk_gb, disk_name = guest_name + "_Disk" + str(disk_num))
                disk_num += 1
        vm_service = vms_service.vm_service(vm.id)
        while vm_service.get().status != types.VmStatus.DOWN:
            time.sleep(1)

        result = "Succesfully created guest: " + guest_name
    except Exception as e:
        result = 'Failed to create VM with disk and NIC: %s' % str(e)

    return result

def getMac(connection, guest_name):
    vms_service = connection.system_service().vms_service()
    vm = vms_service.list(search=guest_name)[0]
    nics_service = vms_service.vm_service(vm.id).nics_service()
    return nics_service.list()[0].mac.address

#def setPXEBootFirst(connection, guest_name):
#    vm = connection.vms.get(name=guest_name)
#    hd_boot_dev = params.Boot(dev='hd')
#    net_boot_dev = params.Boot(dev='network')
#    vm.os.set_boot([net_boot_dev])
#    vm.update()
#    time.sleep(1)
#    vm.os.set_boot([net_boot_dev, hd_boot_dev])
#    vm.update()

#def setPXEBootSecond(connection, guest_name):
#    vm = connection.vms.get(name=guest_name)
#    hd_boot_dev = params.Boot(dev='hd')
#    net_boot_dev = params.Boot(dev='network')
#    vm.os.set_boot([hd_boot_dev])
#    vm.update()
#    time.sleep(1)
#    vm.os.set_boot([hd_boot_dev, net_boot_dev])
#    vm.update()

def powerOnGuest(connection, guest_name):
    vms_service = connection.system_service().vms_service()
    vm = vms_service.list(search=guest_name)[0]
    vm_service = vms_service.vm_service(vm.id)
    try:
        if vm_service.get().status != types.VmStatus.UP:
            print 'Starting VM: %s' % guest_name
            vm_service.start()
            print 'Waiting for VM to reach Up status'
            while vm_service.get().status != types.VmStatus.UP:
                time.sleep(1)
        else:
            print 'VM already up'
    except Exception as e:
        print 'Failed to Start VM: %s\n%s' % (guest_name, str(e))

def powerOffGuest(connection, guest_name):
    vms_service = connection.system_service().vms_service()
    vm = vms_service.list(search=guest_name)[0]
    vm_service = vms_service.vm_service(vm.id)
    try:
        if vm_service.get().status != types.VmStatus.DOWN:
            print 'Stopping VM: %s' % guest_name
            vm_service.stop()
            print 'Waiting for VM to reach Down status'
            while vm_service.get().status != types.VmStatus.DOWN:
                time.sleep(1)
        else:
            print 'VM already down'
    except Exception as e:
        print 'Failed to Stop VM: %s\n%s' % (guest_name, str(e))

def revertToSnapshot(connection, guest_name, snapshot_name, boot_after_restore):
    guest_snapshots = connection.vms.get(guest_name).snapshots.list()
    try:
        for snapshot in guest_snapshots:
            if snapshot.get_description() == snapshot_name:
                print "Snapshot %s found" % snapshot_name
                powerOffGuest(connection, guest_name)
                print "Restoring snapshot"
                snapshot.restore()
                print "Reactivating NIC(s)"
                guest_nics = connection.vms.get(guest_name).nics.list()
                for nic in guest_nics:
                    nic.activate()
                if boot_after_restore == '1':
                    print 'Waiting for VM to finish restoring'
                    while connection.vms.get(guest_name).status.state != types.VmStatus.DOWN:
                        time.sleep(1)
                    powerOnGuest(connection, guest_name)
    except Exception as e:
        print "Failed to revert snapshot '%s' on VM: %s\n%s" % (snapshot_name, guest_name, str(e))

def destroyGuest(connection, guest_name):
    powerOffGuest(connection, guest_name)
    vms_service = connection.system_service().vms_service()
    vm = vms_service.list(search=guest_name)[0]
    vm_service = vms_service.vm_service(vm.id)
    try:
        vm_service.remove()
        print 'Waiting for VM to be deleted'
        while guest_name in [vm.name for vm in vms_service.list()]:
            time.sleep(1)
        result = 'Succesfully removed guest: %s' % guest_name
    except Exception as e:
        result = 'Failed to remove VM: %s\n%s' % (guest_name, str(e))
    return result

def softRebootGuest(connection, guest_name):
    vms_service = connection.system_service().vms_service()
    vm = vms_service.list(search=guest_name)[0]
    vm_service = vms_service.vm_service(vm.id)
    vm_service.reboot()

def hardRebootGuest(connection, guest_name):
    powerOffGuest(connection, guest_name)
    time.sleep(5) #wait for updates
    powerOnGuest(connection, guest_name)
