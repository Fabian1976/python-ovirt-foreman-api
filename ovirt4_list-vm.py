#! /usr/bin/python
#this script requires ovirt-engine-sdk-python
import ovirtsdk4 as sdk
import getpass
from time import sleep

def main():
    url = 'https://rhevm01.infoplus-mgt.ris/ovirt-engine/api'
    username = 'admin@internal'
    password = getpass.getpass("Supply password for user %s: " % username)

    connection = sdk.Connection(url=url, username=username, password=password,insecure=True)
    vms_service = connection.system_service().vms_service()
    vm_list = vms_service.list()
    for vm in vm_list:
        print "Name: %s, memory: %s GB" % (vm.name, vm.memory/1024/1024/1024)
    connection.close()

if __name__ == '__main__':
        main()
