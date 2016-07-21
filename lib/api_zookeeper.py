#! /usr/bin/python

# Created by Fabian van der Hoeven

#this script requires kazoo
from kazoo.client import KazooClient #Zookeeper client class
import kazoo #Zookeeper class

def connectToHost(host, port):
    apiurl=host + ':' + port
    api = kazoo.client.KazooClient(hosts=apiurl)
    api.start()
    return api

def getValue(api, path):
    result = api.get(path)
    return result

def storeValue(api, path, value):
    try:
        api.ensure_path(path)
        api.set(path, value.encode())
        result = "Succesfully stored value '%s' at path '%s'" % (value, path)
    except Exception as e:
        result = "Failed to set value '%s' in zookeeper at path '%s'.\n%s" % (value, path, str(e))
    return result

def deleteValue(api, path, recursive=False):
    try:
        api.delete(path, recursive=recursive)
        result = "Succesfully deleted path '%s'" % path
    except Exception as e:
        result = "Failed to delete path '%s'.\n%s" % (path, str(e))
    return result

def disconnect(api):
    api.stop()
    api.close()
