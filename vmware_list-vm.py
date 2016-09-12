#! /usr/bin/python
import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/lib')
import api_vmware

def main():
    host="man-ms018.recon.man"
    username="b-fvdhoeven"
    password="Feyenoord4ever!"

    vmware_conn = api_vmware.connectToHost(host, username, password)
    vm_list = vmware_conn.get_registered_vms()
    for vm in vm_list:
        print vm
    vmware_conn.disconnect()

if __name__ == '__main__':
        main()
