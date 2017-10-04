#! /usr/bin/python
#this script requires ovirt-engine-sdk-python
import ovirtsdk4 as sdk
from time import sleep

def main():
    URL='https://rhevm01.infoplus-mgt.ris/ovirt-engine/api'
    USERNAME='admin@internal'
    PASSWORD='redhat123'

    connection = sdk.Connection(url=URL, username=USERNAME, password=PASSWORD,insecure=True)
    vms_service = connection.system_service().vms_service()
    vm_list = vms_service.list()
    for vm in vm_list:
        print "Name: %s, memory: %s GB" % (vm.name, vm.memory/1024/1024/1024)
    connection.close()

if __name__ == '__main__':
        main()
