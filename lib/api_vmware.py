#!/usr/bin/python

# Created by Jens Depuydt
# http://www.jensd.be
# http://github.com/jensdepuydt

#this script requires pysphere

from pysphere import VIServer, VIProperty, MORTypes, VIApiException
from pysphere.resources import VimService_services as VI
from pysphere.vi_task import VITask

def connectToHost(host,host_user,host_pw):
    #create server object
    s=VIServer()
    #connect to the host
    try:
        s.connect(host,host_user,host_pw)
        return s
    except VIApiException, err:
        print "Cannot connect to host: '%s', error message: %s" %(host,err)    

def __get_dvsuuid_portgroup(host_con, dc_props, net_name):
    # networkFolder managed object reference
    nf_mor = dc_props.networkFolder._obj
    dvpg_mors = host_con._retrieve_properties_traversal(property_names=['name','key'],from_node=nf_mor, obj_type='DistributedVirtualPortgroup')
    # Get the portgroup managed object.
    dvpg_mor = None
    for dvpg in dvpg_mors:
        if dvpg_mor:
            break
        for p in dvpg.PropSet:
            if p.Name == "name" and p.Val == net_name:
                dvpg_mor = dvpg
            if dvpg_mor:
                break
    if dvpg_mor == None:
        return "Didn't find the network '%s', exiting now" % (net_name)
    # Get the portgroup key
    portgroupKey = None
    for p in dvpg_mor.PropSet:
        if p.Name == "key":
            portgroupKey = p.Val
    # Grab the dvswitch uuid and portgroup properties
    dvswitch_mors = host_con._retrieve_properties_traversal(property_names=['uuid','portgroup'], from_node=nf_mor, obj_type='DistributedVirtualSwitch')
    # Get the appropriate dvswitches managed object
    dvswitch_mor = None
    for dvswitch in dvswitch_mors:
        if dvswitch_mor:
            break
        for p in dvswitch.PropSet:
            if p.Name == "portgroup":
                pg_mors = p.Val.ManagedObjectReference
                for pg_mor in pg_mors:
                    if dvswitch_mor:
                        break
                    key_mor = host_con._get_object_properties(pg_mor, property_names=['key'])
                    for key in key_mor.PropSet:
                        if key.Val == portgroupKey:
                            dvswitch_mor = dvswitch
    # Get the switches uuid
    dvswitch_uuid = None
    for p in dvswitch_mor.PropSet:
        if p.Name == "uuid":
            dvswitch_uuid = p.Val
    return (dvswitch_uuid, portgroupKey)

def createGuest(host_con,guest_dc,guest_dc_folder,guest_host,guest_name,guest_ver,guest_mem,guest_cpu,guest_cores,guest_purpose,guest_iso,guest_os,guest_disks_gb,guest_ds,guest_networks,network_type='standard'):
    #get dc MOR from list
    dc_list=[k for k,v in host_con.get_datacenters().items() if v==guest_dc]
    if dc_list:
        dc_mor=dc_list[0]
    else:
        host_con.disconnect()
        return "Cannot find dc: "+guest_dc
    dc_props=VIProperty(host_con, dc_mor)
    #get vmFolder
    vmf_mor = None
    if guest_dc_folder == '':
        vmf_mor = dc_props.vmFolder._obj
    else:
        #First get all folders from root
        folders = host_con._retrieve_properties_traversal(property_names=['name'], from_node=dc_mor, obj_type='Folder')

        subfolders = guest_dc_folder.split('/')
        found_folder = []
        for sf in subfolders:
            for f in folders:
                if f.PropSet[0].Val == sf:
                    #Get subfolders from found parent folder
                    folders = host_con._retrieve_properties_traversal(property_names=['name'], from_node=f.Obj, obj_type='Folder')
                    found_folder.append(str(f.PropSet[0].Val))
        if found_folder == subfolders:
            vmf_mor = folders[0].Obj
        else:
            print "Datacenter folder '%s' not found. Placing VM in root folder of Datacenter '%s'" % (guest_dc_folder, guest_dc)
            vmf_mor = dc_props.vmFolder._obj
    #get hostfolder MOR
    hf_mor=dc_props.hostFolder._obj
    #get computer resources MORs 
    cr_mors=host_con._retrieve_properties_traversal(property_names=['name','host'],from_node=hf_mor,obj_type='ComputeResource') 
    #get host MOR
    try:
        host_mor=[k for k,v in host_con.get_hosts().items() if v==guest_host][0]
    except IndexError, e:
        host_con.disconnect()
        return "Cannot find host: "+guest_host
    #get computer resource MOR for host 
    cr_mor=None 
    for cr in cr_mors: 
        if cr_mor: 
            break 
        for p in cr.PropSet:
            if p.Name=="host": 
                for h in p.Val.get_element_ManagedObjectReference(): 
                    if h==host_mor: 
                         cr_mor=cr.Obj 
                         break 
                if cr_mor: 
                    break 
    cr_props=VIProperty(host_con,cr_mor) 
    #get resource pool MOR
    rp_mor=cr_props.resourcePool._obj 
    
    #build guest properties    
    #get config target 
    request=VI.QueryConfigTargetRequestMsg() 
    _this=request.new__this(cr_props.environmentBrowser._obj) 
    _this.set_attribute_type(cr_props.environmentBrowser._obj.get_attribute_type()) 
    request.set_element__this(_this) 
    h=request.new_host(host_mor) 
    h.set_attribute_type(host_mor.get_attribute_type()) 
    request.set_element_host(h) 
    config_target=host_con._proxy.QueryConfigTarget(request)._returnval 
    #get default devices 
    request=VI.QueryConfigOptionRequestMsg() 
    _this=request.new__this(cr_props.environmentBrowser._obj) 
    _this.set_attribute_type(cr_props.environmentBrowser._obj.get_attribute_type()) 
    request.set_element__this(_this) 
    h=request.new_host(host_mor) 
    h.set_attribute_type(host_mor.get_attribute_type()) 
    request.set_element_host(h) 
    config_option=host_con._proxy.QueryConfigOption(request)._returnval 
    defaul_devs=config_option.DefaultDevice 
    #get network names
    if guest_networks:
        if len(guest_networks) == 1:
            net_name = guest_networks[0]
            net_names = None
        else:
            net_name = None
            net_names = guest_networks
    else:
        for net in config_target.Network: 
            if net.Network.Accessible: 
                net_name = net.Network.Name 
    #get ds
    ds_target = None 
    for d in config_target.Datastore: 
        if d.Datastore.Accessible and (guest_ds and d.Datastore.Name==guest_ds) or (not guest_ds): 
            ds_target=d.Datastore.Datastore 
            guest_ds=d.Datastore.Name 
            break 
    if not ds_target: 
        host_con.disconnect()
        return "Cannot find datastore: "+guest_ds
    ds_vol_name="[%s]" % guest_ds 
    
    #create task request
    create_vm_request=VI.CreateVM_TaskRequestMsg() 
    config=create_vm_request.new_config()
    #set location of vmx 
    vm_files=config.new_files()
    vm_files.set_element_vmPathName(ds_vol_name) 
    config.set_element_files(vm_files) 
    #set boot parameters
#    vmboot=config.new_bootOptions()
#    vmboot.set_element_enterBIOSSetup(True)
#    config.set_element_bootOptions(vmboot)
    #set general parameters
    config.set_element_version(guest_ver)
    config.set_element_name(guest_name) 
    config.set_element_memoryMB(guest_mem) 
    config.set_element_memoryHotAddEnabled(True)
    config.set_element_numCoresPerSocket(guest_cores)
    config.set_element_numCPUs(guest_cpu*guest_cores)
    config.set_element_guestId(guest_os)
    config.set_element_cpuHotAddEnabled(True)
    config.set_element_annotation(guest_purpose)
    
    #create devices
    devices = [] 
    #add controller to devices
    disk_ctrl_key=1 
    scsi_ctrl_spec=config.new_deviceChange() 
    scsi_ctrl_spec.set_element_operation('add') 
    scsi_ctrl=VI.ns0.ParaVirtualSCSIController_Def("scsi_ctrl").pyclass() 
#    scsi_ctrl=VI.ns0.VirtualLsiLogicController_Def("scsi_ctrl").pyclass() 
    scsi_ctrl.set_element_busNumber(0) 
    scsi_ctrl.set_element_key(disk_ctrl_key) 
    scsi_ctrl.set_element_sharedBus("noSharing") 
    scsi_ctrl_spec.set_element_device(scsi_ctrl)
    devices.append(scsi_ctrl_spec) 
    #find ide controller 
    ide_ctlr = None 
    for dev in defaul_devs: 
        if dev.typecode.type[1] == "VirtualIDEController": 
            ide_ctlr = dev 
    #add cdrom 
    if ide_ctlr: 
        cd_spec = config.new_deviceChange() 
        cd_spec.set_element_operation('add') 
        cd_ctrl = VI.ns0.VirtualCdrom_Def("cd_ctrl").pyclass() 
        cd_device_backing =VI.ns0.VirtualCdromIsoBackingInfo_Def("cd_device_backing").pyclass() 
        ds_ref = cd_device_backing.new_datastore(ds_target) 
        ds_ref.set_attribute_type(ds_target.get_attribute_type()) 
        cd_device_backing.set_element_datastore(ds_ref) 
        cd_device_backing.set_element_fileName("%s %s" % (ds_vol_name,guest_iso)) 
        cd_ctrl.set_element_backing(cd_device_backing) 
        cd_ctrl.set_element_key(20) 
        cd_ctrl.set_element_controllerKey(ide_ctlr.get_element_key()) 
        cd_ctrl.set_element_unitNumber(0) 
        cd_spec.set_element_device(cd_ctrl) 
        devices.append(cd_spec) 
    #add disk
    disk_spec=config.new_deviceChange() 
    disk_spec.set_element_fileOperation("create") 
    disk_spec.set_element_operation("add") 
    disk_ctlr=VI.ns0.VirtualDisk_Def("disk_ctlr").pyclass() 
    disk_backing=VI.ns0.VirtualDiskFlatVer2BackingInfo_Def("disk_backing").pyclass() 
    disk_backing.set_element_fileName(ds_vol_name) 
    disk_backing.set_element_diskMode("persistent") 
    disk_backing.set_element_eagerlyScrub(True)
    disk_ctlr.set_element_key(0) 
    disk_ctlr.set_element_controllerKey(disk_ctrl_key) 
    disk_ctlr.set_element_unitNumber(0) 
    disk_ctlr.set_element_backing(disk_backing) 
    guest_disk_size=int(guest_disks_gb[0])*1024*1024
    disk_ctlr.set_element_capacityInKB(guest_disk_size) 
    disk_spec.set_element_device(disk_ctlr) 
    devices.append(disk_spec)
    #create remaining disks
    if len(guest_disks_gb) > 1:
        unit_number = 1
        for guest_disk_gb in guest_disks_gb[1:]:

            disk_spec=config.new_deviceChange()
            disk_spec.set_element_fileOperation("create")
            disk_spec.set_element_operation("add")
            disk_ctlr=VI.ns0.VirtualDisk_Def("disk_ctlr").pyclass()
            disk_backing=VI.ns0.VirtualDiskFlatVer2BackingInfo_Def("disk_backing").pyclass()
            disk_backing.set_element_fileName(ds_vol_name)
            disk_backing.set_element_diskMode("persistent")
            disk_ctlr.set_element_key(0)
            disk_ctlr.set_element_controllerKey(disk_ctrl_key)
            disk_ctlr.set_element_unitNumber(unit_number)
            disk_ctlr.set_element_backing(disk_backing)
            guest_disk_size=int(guest_disk_gb)*1024*1024
            disk_ctlr.set_element_capacityInKB(guest_disk_size)
            disk_spec.set_element_device(disk_ctlr)
            devices.append(disk_spec)
            unit_number += 1

    #add a network controller
    if net_names:
        for net_name in net_names:
            nic_spec = config.new_deviceChange()
            nic_spec.set_element_operation("add")
            nic_ctlr = VI.ns0.VirtualVmxnet3_Def("nic_ctlr").pyclass()
            if network_type == 'dvs':
                #get distributed vswitch uuid and portgroup number of net_name
                (dvswitch_uuid, portgroupKey) = __get_dvsuuid_portgroup(host_con, dc_props, net_name)
                #create the device
                nic_backing_port = VI.ns0.DistributedVirtualSwitchPortConnection_Def("nic_backing_port").pyclass()
                nic_backing_port.set_element_switchUuid(dvswitch_uuid)
                nic_backing_port.set_element_portgroupKey(portgroupKey)
                nic_backing = VI.ns0.VirtualEthernetCardDistributedVirtualPortBackingInfo_Def("nic_backing").pyclass()
                nic_backing.set_element_port(nic_backing_port)
            elif network_type == 'standard':
                # Standard switch
                nic_backing = VI.ns0.VirtualEthernetCardNetworkBackingInfo_Def("nic_backing").pyclass()
                nic_backing.set_element_deviceName(net_name)
            else:
                return "Unknown network type '%s'" % network_type
            nic_ctlr.set_element_addressType("generated")
            nic_ctlr.set_element_backing(nic_backing)
            nic_ctlr.set_element_key(4)
            nic_spec.set_element_device(nic_ctlr)
            devices.append(nic_spec)
    else:
        nic_spec = config.new_deviceChange()
        nic_spec.set_element_operation("add")
        nic_ctlr = VI.ns0.VirtualVmxnet3_Def("nic_ctlr").pyclass()
        if network_type == 'dvs':
            #get distributed vswitch uuid and portgroup number of net_name
            (dvswitch_uuid, portgroupKey) = __get_dvsuuid_portgroup(host_con, dc_props, net_name)
            #create the device
            nic_backing_port = VI.ns0.DistributedVirtualSwitchPortConnection_Def("nic_backing_port").pyclass()
            nic_backing_port.set_element_switchUuid(dvswitch_uuid)
            nic_backing_port.set_element_portgroupKey(portgroupKey)
            nic_backing = VI.ns0.VirtualEthernetCardDistributedVirtualPortBackingInfo_Def("nic_backing").pyclass()
            nic_backing.set_element_port(nic_backing_port)
        elif network_type == 'standard':
            # Standard switch
            nic_backing = VI.ns0.VirtualEthernetCardNetworkBackingInfo_Def("nic_backing").pyclass()
            nic_backing.set_element_deviceName(net_name)
        else:
            return "Unknown network type '%s'" % network_type
        nic_ctlr.set_element_addressType("generated")
        nic_ctlr.set_element_backing(nic_backing)
        nic_ctlr.set_element_key(4)
        nic_spec.set_element_device(nic_ctlr)
        devices.append(nic_spec)
    
    #create vm request
    config.set_element_deviceChange(devices) 
    create_vm_request.set_element_config(config)
    new_vmf_mor=create_vm_request.new__this(vmf_mor) 
    new_vmf_mor.set_attribute_type(vmf_mor.get_attribute_type()) 
    new_rp_mor=create_vm_request.new_pool(rp_mor) 
    new_rp_mor.set_attribute_type(rp_mor.get_attribute_type()) 
    new_host_mor=create_vm_request.new_host(host_mor) 
    new_host_mor.set_attribute_type(host_mor.get_attribute_type()) 
    create_vm_request.set_element__this(new_vmf_mor) 
    create_vm_request.set_element_pool(new_rp_mor) 
    create_vm_request.set_element_host(new_host_mor) 
    
    #finally actually create the guest :)
    task_mor=host_con._proxy.CreateVM_Task(create_vm_request)._returnval 
    task=VITask(task_mor,host_con) 
    task.wait_for_state([task.STATE_SUCCESS,task.STATE_ERROR]) 
    
    if task.get_state()==task.STATE_ERROR: 
        return "Cannot create guest: "+task.get_error_message()
    else:
        return "Succesfully created guest: "+guest_name

def getMac(host_con,guest_name):
    vm=host_con.get_vm_by_name(guest_name)
    net = vm.get_property('net', from_cache=False)
    if net:
        for interface in net:
            mac = interface.get('mac_address', None)
            if mac:
                return mac

    #for v in vm.get_property("devices").values():
    #    if v.get('macAddress'):
    #        return v.get('macAddress')
    
    devs = vm.get_property('devices')
    result = []
    for dev in devs:
       if devs[dev]['type'] == 'VirtualVmxnet3':
          result.append(devs[dev]['macAddress'])
    return result

def powerOnGuest(host_con,guest_name):
    try:
        if host_con.get_vm_by_name(guest_name).get_status() != 'POWERED ON':
            print 'Starting VM: %s' % guest_name
            host_con.get_vm_by_name(guest_name).power_on()
            print 'Waiting for VM to reach Up status'
            while host_con.get_vm_by_name(guest_name).get_status() != 'POWERED ON':
                sleep(1)
        else:
            print 'VM already up'
    except Exception as e:
        print 'Failed to Start VM: %s\n%s' % (guest_name, str(e))

def powerOffGuest(host_con,guest_name):
    try:
        if host_con.get_vm_by_name(guest_name).get_status() != 'POWERED OFF':
            print 'Stopping VM: %s' % guest_name
            host_con.get_vm_by_name(guest_name).power_off()
            print 'Waiting for VM to reach Down status'
            while host_con.get_vm_by_name(guest_name).get_status() != 'POWERED OFF':
                sleep(1)
        else:
            print 'VM already down'
    except Exception as e:
        print 'Failed to Stop VM: %s\n%s' % (guest_name, str(e))

def destroyGuest(host_con, guest_name):
    powerOffGuest(host_con, guest_name)
    try:
        vm = host_con.get_vm_by_name(guest_name)
        request = VI.Destroy_TaskRequestMsg()
        _this = request.new__this(vm._mor)
        _this.set_attribute_type(vm._mor.get_attribute_type())
        request.set_element__this(_this)
        ret = host_con._proxy.Destroy_Task(request)._returnval
        task = VITask(ret, host_con)
        print 'Waiting for VM to be deleted'
        status = task.wait_for_state([task.STATE_SUCCESS, task.STATE_ERROR])
        if status == task.STATE_SUCCESS:
            result = 'Succesfully removed guest: %s' % guest_name
        elif status == task.STATE_ERROR:
            result = 'Failed to remove VM: %s\n%s' % (guest_name, task.get_error_message())
    except Exception as e:
        result = 'Failed to remove VM: %s\n%s' % (guest_name, str(e))
    return result

