#! /usr/bin/python
#
# Created by Fabian van der Hoeven
import ipahttp
import sys

def connectToHost(host, host_user, host_pwd):
    api = ipahttp.ipa(host)
    result = api.login(host_user, host_pwd)
    if result:
        if result.status_code <> 200:
            print "Unable to login to IPA-server. Status code: %s" % result.status_code
            sys.exit(99)
    else:
        print "Unable to login to IPA-server"
        sys.exit(99)
    return api

def add_host_hostgroup(api, hostgroup, host):
    api.hostgroup_add_member(hostgroup, host)

