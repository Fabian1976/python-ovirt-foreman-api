#! /usr/bin/python
#
# Created by Fabian van der Hoeven
import ipahttp

def connectToHost(host, host_user, host_pwd):
    api = ipahttp.ipa(host)
    api.login(host_user, host_pwd)
    return api

def add_host_hostgroup(api, hostgroup, host):
    api.hostgroup_add_member(hostgroup, host)

