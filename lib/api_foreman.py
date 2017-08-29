#! /usr/bin/python

# Created by Fabian van der Hoeven

#this script requires ovirt-engine-sdk-python
from foreman.client import Foreman
import sys
import time

def connectToHost(host, host_user, host_pwd):
    apiurl="http://"+host
    #insecure -> skips SSL check
    api = Foreman(apiurl, (host_user, host_pwd), api_version=2)
    return api

def createGuest(api, guest_name, guest_hostgroup, guest_domain, guest_organization, guest_location, guest_mac_address, guest_subnet, guest_environment, guest_ptable, guest_build='false', guest_ip_address = None):
    guest_hostgroup_id = getHostgroupId(api, guest_hostgroup)
    if guest_hostgroup_id == 0:
        print "Hostgroup '%s' not found. Cannot continue" % guest_hostgroup
        sys.exit(1)
    guest_domain_id = getDomainId(api, guest_domain)
    if guest_domain_id == 0:
        print "Domain '%s' not found. Cannot continue" % guest_domain
        sys.exit(1)
    guest_organization_id = getOrganizationId(api, guest_organization)
    if guest_organization_id == 0:
        print "Organization '%s' not found. Cannot continue" % guest_organization
        sys.exit(1)
    guest_location_id = getLocationId(api, guest_location)
    if guest_location_id == 0:
        print "Location '%s' not found. Cannot continue" % guest_location
        sys.exit(1)
    guest_subnet_list =  guest_subnet.split(",")
    guest_subnet_test = getSubnetId(api, guest_subnet_list[0])
    if guest_subnet_test == 0:
        print "Subnet '%s' not found. Cannot continue" % guest_subnet_test
        sys.exit(1)

    # guest_ip_address passed as string , creating a list for itteration
    if guest_ip_address:
        guest_ip_address_list =  guest_ip_address.split(",")
    else:
        guest_ip_address_list = []
 
    guest_environment_id = getEnvironmentId(api, guest_environment)
    if guest_environment_id == 0:
        print "Environment '%s' not found. Cannot continue" % guest_environment
        sys.exit(1)
    guest_ptable_id = getPtableId(api, guest_ptable)
    if guest_ptable_id == 0:
        print "Partition table '%s' not found. Cannot continue" % guest_ptable
        sys.exit(1)
    
    # Only build interface_attributs for additional interfaces. first element is primairy interface , second is the start for interface_attribuites 
    #check if mac_address is string (ovirt) or array (vmware)
    if isinstance(guest_mac_address, str):
        guest_mac_address = [guest_mac_address]
    interface_attributes = []  
    if len(guest_subnet_list) > 1:
       for i in xrange(1,len(guest_subnet_list)):
         interface_attributes.append({'identifier': 'eth'+str(i) , 'ip': guest_ip_address_list[i] , 'subnet_id': getSubnetId(api, guest_subnet_list[i]), 'mac': guest_mac_address[i],'type': 'interface','managed': 'true' })
    
    try:
        hosts = api.hosts.index()['results']
        # Found multi NIC config
        if (len(guest_ip_address_list)>1):
            print "Found IP Address : %s , continue" % guest_ip_address_list[0]
            # Inform IP addresses found
            for i in xrange(1,len(guest_ip_address_list)):
               print "Found Additional IP Address : %s , continue" % guest_ip_address_list[i]
            # Build host
            api.hosts.create(host={'name': guest_name,
                                   'mac': guest_mac_address[0],
                                   'ip': guest_ip_address_list[0],
                                   'hostgroup_id': guest_hostgroup_id,
                                   'build': guest_build,
                                   'domain_id': guest_domain_id,
                                   'organization_id': guest_organization_id,
                                   'location_id': guest_location_id,
                                   'subnet_id': getSubnetId(api, guest_subnet_list[0]),
                                   'environment_id': guest_environment_id,
                                   'ptable_id': guest_ptable_id,
                                   'interfaces_attributes': interface_attributes
                                   }
                            )
        # Found single NIC config
        elif (len(guest_ip_address_list)==1): 
            print "Found IP Address : %s , continue" % guest_ip_address_list[0]
            api.hosts.create(host={'name': guest_name, 
                                   'mac': guest_mac_address[0], 
                                   'ip': guest_ip_address_list[0], 
                                   'hostgroup_id': guest_hostgroup_id, 
                                   'build': guest_build, 
                                   'domain_id': guest_domain_id, 
                                   'organization_id': guest_organization_id, 
                                   'location_id': guest_location_id, 
                                   'subnet_id': getSubnetId(api, guest_subnet_list[0]),
                                   'environment_id': guest_environment_id, 
                                   'ptable_id': guest_ptable_id
                                  }
                            )
        # Found no IP config , DHCP ?
        else :
            api.hosts.create(host={'name': guest_name, 
                                   'mac': guest_mac_address[0], 
                                   'hostgroup_id': guest_hostgroup_id, 
                                   'build': guest_build, 
                                   'domain_id': guest_domain_id, 
                                   'organization_id': guest_organization_id, 
                                   'location_id': guest_location_id, 
                                   'subnet_id': getSubnetId(api, guest_subnet_list[0]),
                                   'environment_id': guest_environment_id, 
                                   'ptable_id': guest_ptable_id
                                  }
                            )
        result = "Succesfully created guest: " + guest_name
    except Exception as e:
        result = "Failed to create host '%s' in Foreman.\n%s" % (guest_name, str(e))
    return result

def destroyGuest(api, guest_name):
    guest_host_id = getHostId(api, guest_name)
    if guest_host_id == 0:
        print "Host '%s' not found. Cannot continue" % guest_name
        sys.exit(1)
    try:
        api.hosts.destroy(guest_host_id)
        result = "Succesfully removed guest: " + guest_name
    except Exception as e:
        result = "Failed to remove host '%s' in Foreman.\n%s" % (guest_name, str(e))
    return result

def getHostgroupId(api, hostgroupName):
    hostgroups = api.index_hostgroups()['results']
    for hostgroup in hostgroups:
        if hostgroup['name'] == hostgroupName:
            hostgroupId = hostgroup['id']
            break
        else:
            hostgroupId = 0
    return hostgroupId

def getDomainId(api, domainName):
    domains = api.index_domains()['results']
    for domain in domains:
        if domain['name'] == domainName:
            domainId = domain['id']
            break
        else:
            domainId = 0
    return domainId

def getOrganizationId(api, organizationName):
    # Kan middels python api geen organizations ophalen. Kan wel handmatig: http://<foreman_url>/api/organizations, dus hier maar met een dictionary
    organizations = []
    organization = {}
    organization['id'] = 3
    organization['name'] = 'CMC'
    organizations.append(organization)

    for organization in organizations:
        if organization['name'] == organizationName:
            organizationId = organization['id']
            break
        else:
            organizationId = 0
    return organizationId

def getLocationId(api, locationName):
    locations = api.index_locations()['results']
    for location in locations:
        if location['name'] == locationName:
            locationId = location['id']
            break
        else:
            locationId = 0
    return locationId

def getSubnetId(api, subnetName):
    subnets = api.index_subnets()['results']
    for subnet in subnets:
        if subnet['name'] == subnetName:
            subnetId = subnet['id']
            break
        else:
            subnetId = 0
    return subnetId

def getEnvironmentId(api, environmentName):
    environments = api.index_environments()['results']
    for environment in environments:
        if environment['name'] == environmentName:
            environmentId = environment['id']
            break
        else:
            environmentId = 0
    return environmentId

def getPtableId(api, ptableName):
    ptables = api.index_ptables()['results']
    for ptable in ptables:
        if ptable['name'] == ptableName:
            ptableId = ptable['id']
            break
        else:
            ptableId = 0
    return ptableId

def getHostId(api, hostName):
    hosts = api.index_hosts(search=hostName)['results']
    for host in hosts:
        if host['name'] == hostName:
            hostId = host['id']
            break
        else:
            hostId = 0
    return hostId

def getHostIP(api, hostName):
    try:
        return str(api.index_hosts(search=hostName)['results'][0]['ip'])
    except IndexError:
        print "Host %s not found" % hostName
        return -1

def buildHost(api, hostName):
    hostResults = api.index_hosts(search=hostName)['results']
    if len(hostResults) <> 1:
        print "Did not get 1 result with search '%s'. Got '%s'. Please refine your search" % (hostName, len(hostResults))
        result = -1
    else:
        #needs to run twice for some reason
        apiresult = api.hosts.update({'build':True}, int(hostResults[0]['id']))
        apiresult = api.hosts.update({'build':True}, int(hostResults[0]['id']))
        result = "Host '%s' successfully set to build mode" % hostName
    return result

def createParameters(api, hostName, parameters):
    hostResults = api.index_hosts(search=hostName)['results']
    for parameter in parameters:
        real_parameter = {}
        parameterCreated = False
        for k, v in parameter.iteritems():
            real_parameter['name'] = k
            real_parameter['value'] = v
        while not parameterCreated:
            api.hosts.parameters_create(real_parameter, hostResults[0]['id'])
            parameterResults = api.hosts.parameters_index(hostResults[0]['id'])['results']
            for parameterResult in parameterResults:
                if real_parameter['name'] == parameterResult['name']:
                    parameterCreated = True
            time.sleep(3)

        print "Succesfully created parameter: %s" % parameter
