# python-ovirt-foreman-api
Python scripts to interact with oVirt and Foreman for automatic server deployment and provisioning

## Requirements
* CentOS / RHEL 7 machine

Some scripts of this repo assume a specific environment:
* deploy-and-build-vm.py
  * ovirt / rhev hypervisor
  * foreman (pxe)
  * Zookeeper (to store the server role. Zookeeper is used as a hiera backend for the puppetmaster)
  * Puppetmaster (not needed to just deploy a server, but is is needed when you want to auto-provision a server upon creation)
* destroy-vm.py
  * ovirt / rhev hypervisor
  * foreman (to remove host record)
  * Zookeeper (removes role and ossec auth information)
  * Puppetmaster (revokes certificate of host)
* revert-vm-to-snapshot.py
  * ovirt / rhev hypervisor
* ovirt-list-vm.py
  * ovirt / rhev hypervisor

## Dependencies installation
Not all scripts need the same packages to be installed.
These steps are needed for all scripts to work:
```bash
# yum install python-pip gcc python-devel libxml2-devel
# pip install --upgrade pip
# pip install ovirt-engine-sdk-python
# pip install simple-crypt
```

The scripts `revert-vm-to-snapshot.py` and `ovirt-list-vm.py` should function now.

The other scripts also need these packages:
```bash
# pip install pysphere
# pip install python-foreman
# pip install kazoo
# pip install https://github.com/daradib/pypuppet/archive/master.tar.gz
# pip install pyyaml
```

## Installation
```bash
# yum install git
$ git clone https://github.com/Fabian1976/python-ovirt-foreman-api.git
```

## Usage
All scripts use a custom config class to read the config file. Because of this, all config files must have the same structure and same fields, even if you don't need those fields.
Based on the script you use the specific fields are used.

You can find an example config file in the vm\_config folder.

The usage of each script is very easy and simular:
```
<script_name> <config_file>
```

If you plan on comunicating with a puppetmaster, be sure to create the appropiate SSL certificates and autherization configuration on the puppetmaster. The steps below will describe how to enable the destroy script to revoke a certificate for the destroyed host.

Perform these steps on the puppetmaster:
```
# puppet cert generate api
```

This will generate theze 2 files:
```
/etc/puppetlabs/puppet/ssl/certs/api.pem
/etc/puppetlabs/puppet/ssl/private_keys/api.pem
```

In the folder where the scripts are located, create a folder called `ssl` and copy the files from the previous step.
* /etc/puppetlabs/puppet/ssl/certs/api.pem should be named api-cert.pem
* /etc/puppetlabs/puppet/ssl/private\_keys/api.pem should be named api-key.pem

On the puppetmaster modify this file `/etc/puppetlabs/puppetserver/conf.d/auth.conf` and add this block:
```
        {
            # Allow api to destroy certificates
            match-request: {
                path: "/puppet-ca/v1/certificate_status"
                type: path
                method: [delete]
            }
            allow: "api"
            sort-order: 500
            name: "API destroy cert"
        },
```

All should be functioning now.
