#! /usr/bin/python
#this script requires ovirt-engine-sdk-python
from ovirtsdk.api import API
from ovirtsdk.xml import params
from time import sleep

def main():
    URL='https://poc-ovirtm1.infoplus-ot.ris:443/api'
    USERNAME='admin@internal'
    PASSWORD='redhat'

    api = API(url=URL, username=USERNAME, password=PASSWORD,insecure=True)
    vm_list=api.vms.list()
    for vm in vm_list:
        print vm.name
    api.disconnect()

if __name__ == '__main__':
        main()
