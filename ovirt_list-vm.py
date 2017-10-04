#! /usr/bin/python
#this script requires ovirt-engine-sdk-python
from ovirtsdk.api import API
from ovirtsdk.xml import params
import getpass
from time import sleep

def main():
    url='https://poc-ovirtm1.infoplus-ot.ris:443/api'
    username='admin@internal'
    password=getpass.getpass("Supply password for user %s: " % username)

    api = API(url=url, username=username, password=password,insecure=True)
    vm_list=api.vms.list()
    for vm in vm_list:
        print vm.name
    api.disconnect()

if __name__ == '__main__':
        main()
