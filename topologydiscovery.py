"""
   Copyright 2017 Phil Zampino

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import httplib2 as http
import json
import base64
import re
import sys

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


# Headers used for all REST invocations during discovery
headers = {
    'Content-Type': 'application/json; charset=UTF-8',
}

#http.debuglevel = 1

service_config_type_map = { 
    "HIVE"  : "hive-site",
    "OOZIE" : "oozie-site",
    "HDFS"  : "hdfs-site",
    "YARN"  : "yarn-site",
    "HBASE" : "hbase-site"
}

component_config_property_map = {
    "NAMENODE"        : {"HDFS"  : "hdfs-site"},
    "RESOURCEMANAGER" : {"YARN"  : service_config_type_map.get("YARN")},
    "OOZIE_SERVER"    : {"OOZIE" :service_config_type_map.get("OOZIE")},
    "HIVE_SERVER"     : {"HIVE"  :service_config_type_map.get("HIVE")},
    "WEBHCAT_SERVER"  : {"HIVE"  : "webhcat-site"}
}

def print_json(data):
    print json.dumps(data, indent=4)


def invoke_rest(target_url, username, password):
  target = urlparse(target_url)
  method = 'GET'
  body = ''

  headers.update({'Authorization' : 'Basic ' + base64.encodestring( username + ':' + password )})

  h = http.Http()
  response, content = h.request(target.geturl(),
                                method,
                                body,
                                headers)

  # Assume that content is JSON
  return json.loads(content)


def print_cluster_component_hosts(cluster):
    components = cluster.get_components()
    print '{:_<8} {:_<16} {:_<25} {:_<30}'.format('', '', '', '')
    print '{:^8} {:^16} {:^25} {:^30}'.format('Cluster', 'Service', 'Component', 'Host(s)')
    print '{:_<8} {:_<16} {:_<25} {:_<30}'.format('', '', '', '')
    for comp_name in components:
        comp = components.get(comp_name)
        print '{:8} {:16} {:25} {}'.format(comp.get_cluster(), comp.get_service(), comp.get_name(), comp.get_hostnames())


def print_cluster_service_configs(cluster):
    for service_name in cluster.service_config_data:
        print service_name
        for config_type in cluster.service_config_data.get(service_name):
            print '\tconfig type: ' + config_type
#            print_json(cluster.service_config_data.get(service_name).get(config_type))
            

def print_cluster_service_siteconfig_properties(cluster):
    for service_name in cluster.service_config_data:
        for config_type in cluster.service_config_data.get(service_name):
            if config_type.endswith('-site'):
                print service_name + ': ' + config_type
                config = cluster.service_config_data.get(service_name)
                print_json(config.get('properties'))
            


def print_cluster_component_configs_of_interest(cluster):
    for component_name in component_config_property_map:
            print component_name
            comps = cluster.get_components()
            comp = comps.get(component_name)
            if comp is None:
                print '  The cluster does not include info about component: ' + component_name
            else:
                service_mapping = component_config_property_map.get(component_name)
                for service in service_mapping:
                    print '  ' + service
                    service_configs = service_mapping.get(service)
                    for config in service_configs:
                        print '    {}'.format(config)
                        config_props = service_configs.get(config)
                        for prop in config_props:
                            print '      {:36} : {}'.format(prop, comp.get_config_property(prop))




class Cluster(object):
    
    discovery_address = None
    service_config_data = {}
    component_hosts = {}

    '''
    Discover the clusters available from the specified Ambari host
    :return: A dict of cluster names to discovered Cluster objects
    '''
    @staticmethod
    def discover(ambari_url, username, password):
        discovered = {}
        clusters_response = invoke_rest(ambari_url + '/api/v1/clusters', username, password)

        clusters_data = clusters_response.get('items')
        for cluster_data in clusters_data:
            c = Cluster(ambari_url, cluster_data, username, password)
            discovered[c.get_name()] = c

        return discovered


    def __init__(self, discovery_address, data, username, password):
        self.username = username
        self.password = password
        self.discovery_address = discovery_address
        self.href = data.get('href')
        cluster_details = data.get('Clusters')
        self.name = cluster_details.get('cluster_name')
        self.version = cluster_details.get('version')
        self.__init_service_configs__()
        self.__init_component_hosts__()
        self.__init_components__()

    def __init_component_hosts__(self):
        response = invoke_rest(self.get_component_hostroles_href(), self.username, self.password)
        for item in response.get('items'):
            for component in item.get('components'):
                for host_component in component.get('host_components'):
                    host_roles = host_component.get('HostRoles')
                    if self.component_hosts.get(host_roles.get("component_name")) is None:
                        self.component_hosts[host_roles.get("component_name")] = []
                    self.component_hosts.get(host_roles.get("component_name")).append(host_roles.get("host_name"))
 

    def __init_service_configs__(self):
        response = invoke_rest(self.get_serviceconfigs_href(), self.username, self.password)
        for service in response.get('items'):
            service_name = service.get('service_name')
            self.service_config_data[service_name] = {}
            for service_config in service.get('configurations'):
                self.service_config_data[service_name][service_config.get('type')] = service_config


    def __init_components__(self):
        self.components = {}
        response = invoke_rest(self.get_components_href(), self.username, self.password)
        #    print_json(response)
        for component_data in response.get('items'):
            c = Component(self, component_data)
            self.components[c.get_name()] = c

    def get_component_hostroles_href(self):
        return '{}/api/v1/clusters/{}/services?fields=components/host_components/HostRoles/'.format(self.discovery_address, self.name)

    def get_serviceconfigs_href(self):
        return '{}/api/v1/clusters/{}/configurations/service_config_versions?is_current=true'.format(self.discovery_address, self.name)

    def get_components_href(self):
        return '{}/api/v1/clusters/{}/components'.format(self.discovery_address, self.name)

    def get_name(self):
        return self.name

    def get_version(self):
        return self.version

    def get_href(self):
        return self.href

    def get_components(self):
        return self.components

    def get_component(self, comp_name):
        return self.components.get(comp_name)



class Component(object):

    config_props = {}

    def __init__(self, cluster, data):
        self.href = data.get('href')
        sci = data.get('ServiceComponentInfo')
        self.name = sci.get('component_name')
        self.service = sci.get('service_name')
        self.cluster = sci.get('cluster_name')
        self.hostnames = []

        # Determine the associated host name
        component_hostnames = cluster.component_hosts.get(self.name)
        if component_hostnames is not None:
            self.hostnames.extend(component_hostnames)

        # Determine additional address details
        if self.name in component_config_property_map:
            mapping = component_config_property_map.get(self.name)
            for service in mapping:
                config = mapping.get(service)
                self.config_props = cluster.service_config_data.get(service).get(config).get('properties')

    def get_name(self):
        return self.name

    def get_service(self):
        return self.service

    def get_cluster(self):
        return self.cluster

    def get_href(self):
        return self.href

    def get_hostnames(self):
        return self.hostnames

    def get_config_properties(self):
        return self.config_props

    def get_config_property(self, prop_name):
        return self.config_props.get(prop_name)


class AmbariNameNodeServiceURLBuilder(object):
    def build_url(self, cluster):
        namenode_component = cluster.get_component("NAMENODE")
        namenode_rpc_address = namenode_component.get_config_property("dfs.namenode.rpc-address")
        namenode_url = 'hdfs://{}'.format(namenode_rpc_address)
        return namenode_url

class AmbariJobTrackerServiceURLBuilder(object):
    def build_url(self, cluster):
        jobtracker_url = 'rpc://{}'.format(cluster.get_component("RESOURCEMANAGER").get_config_property('yarn.resourcemanager.address'))
        return jobtracker_url

class AmbariWebHDFSServiceURLBuilder(object):
    def build_url(self, cluster):
        webhdfs_address = cluster.service_config_data.get('HDFS').get('hdfs-site').get('properties').get('dfs.namenode.http-address')
        webhdfs_url = 'http://{}/webhdfs'.format(webhdfs_address)
        return webhdfs_url


class AmbariWebHCATServiceURLBuilder(object):
    def build_url(self, cluster):
        webhcat_component = cluster.get_component('WEBHCAT_SERVER')
        webhcat_port = webhcat_component.get_config_property('templeton.port')
        webhcat_host = webhcat_component.get_hostnames()[0]
        webhcat_url = 'http://{}:{}/templeton'.format(webhcat_host, webhcat_port)
        return webhcat_url


class AmbariOozieServiceURLBuilder(object):
    def build_url(self, cluster):
        oozie_component = cluster.get_component('OOZIE_SERVER')
        oozie_url = '{}'.format(oozie_component.get_config_property('oozie.base.url'))
        return oozie_url

class AmbariWebHBaseServiceURLBuilder(object):
    def build_url(self, cluster):
        webhbase_host = cluster.component_hosts.get('HBASE_MASTER')[0]
        webhbase_url = 'http://{}:{}'.format(webhbase_host, '60080')
        return webhbase_url


class AmbariHiveServiceURLBuilder(object):
    def build_url(self, cluster):
        hive_server_component = cluster.get_component("HIVE_SERVER")
        hive_server_path = hive_server_component.get_config_property('hive.server2.thrift.http.path')
        hive_server_http_port = hive_server_component.get_config_property('hive.server2.thrift.http.port')
        hive_server_transport_mode = hive_server_component.get_config_property('hive.server2.transport.mode')
        hive_server_use_ssl = hive_server_component.get_config_property('hive.server2.use.SSL')
        hive_server_host = hive_server_component.get_hostnames()[0]
        hive_server_scheme = ''
        if hive_server_transport_mode == 'http':
            if hive_server_use_ssl is 'true':
                hive_server_scheme = 'https'
            else:
                hive_server_scheme = 'http'
        hive_server_url = '{}://{}:{}/{}'.format(hive_server_scheme, hive_server_host, hive_server_http_port, hive_server_path)
        return hive_server_url

class AmbariResourceManagerURLBuilder(object):
    def build_url(self, cluster):
        resman_component = cluster.get_component("RESOURCEMANAGER")
        resman_webappaddress = resman_component.get_config_property('yarn.resourcemanager.webapp.address')
        yarn_http_policy = resman_component.get_config_property('yarn.http.policy')
        resman_scheme = 'http'
        if yarn_http_policy is 'HTTPS_ONLY':
            resman_scheme = 'https'
        resman_url = '{}://{}/ws'.format(resman_scheme, resman_webappaddress)
        return resman_url


class TopologyDiscovery(object):

    service_url_builders = {
        'NAMENODE'        : AmbariNameNodeServiceURLBuilder(),
        'JOBTRACKER'      : AmbariJobTrackerServiceURLBuilder(),
        'WEBHDFS'         : AmbariWebHDFSServiceURLBuilder(),
        'WEBHCAT'         : AmbariWebHCATServiceURLBuilder(),
        'OOZIE'           : AmbariOozieServiceURLBuilder(),
        'WEBHBASE'        : AmbariWebHBaseServiceURLBuilder(),
        'HIVE'            : AmbariHiveServiceURLBuilder(),
        'RESOURCEMANAGER' : AmbariResourceManagerURLBuilder()
    }
    supported_url_builders = service_url_builders.keys()

    clusters = {}

    @staticmethod
    def discover(url, username, password):
        return TopologyDiscovery(Cluster.discover(url, username, password))

    def __init__(self, clusters):
        self.clusters.update(clusters)

    def get_clusters(self):
        return self.clusters

    def get_cluster(self, cluster_name):
        return self.clusters.get(cluster_name)

    def get_service_url(self, cluster_name, service_name):
        service_url = None
        c = self.get_cluster(cluster_name)
        if service_name in self.supported_url_builders:
            service_url = self.service_url_builders.get(service_name).build_url(c)
        else:
            print service_name + ' is not currently supported by this module.'
        return service_url

