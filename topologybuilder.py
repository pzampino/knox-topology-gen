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
import yaml
from os.path import basename, splitext
from topologydiscovery import TopologyDiscovery


class TopologyBuilder(object):
	def build(self, simple_descriptor, username, password):
		discovery_registry = None
		provider_config = None
		config_services = []

		with open(simple_descriptor) as file:
			config = yaml.load(file)

			#self.display_descriptor_contents(simple_descriptor, config)
			discovery_registry = config.get('discovery-registry')
			provider_config = config.get('provider-config-ref')
			cluster = config.get('cluster')
			# Services to configure
			services = config.get('services')
			for service in services:
				config_services.append(service)

		# Perform the service discovery
		topology_discovery = TopologyDiscovery.discover(discovery_registry, username, password)

		service_urls = self.get_service_urls(topology_discovery, cluster, config_services)
		self.display_discovered_service_urls(service_urls)

        # Create the full topology file based on the simple descriptor 
		self.write_topology_xml(basename(splitext(simple_descriptor)[0]), provider_config, service_urls)


	def get_service_urls(self, discovery, cluster_name, services):
		service_url_map = []
		for service in services:
			service_name = service.get('name')
			# If the service URL is included, then use it
			if (service.has_key('url')):
				service_url = service.get('url')
			else: # Otherwise, apply the discovery result
				service_url = discovery.get_service_url(cluster_name, service_name);

			service_url_map.append(tuple([service_name, service_url]))
		return service_url_map


	def write_topology_xml(self, descriptor_name, provider_config, service_urls):
		descriptor_file_name = descriptor_name + '.xml'
		with open(descriptor_file_name, 'w') as descriptor:
			descriptor.write('<topology>\n')

			with open(provider_config) as providers:
				for line in providers:
					descriptor.write(line)

			for service in service_urls:
				descriptor.write('    <service>\n')
				descriptor.write('        <role>{}</role>\n'.format(service[0]))
				descriptor.write('        <url>{}</url>\n'.format(service[1]))
				descriptor.write('    </service>\n')

			descriptor.write('</topology>\n')
		print '\nGenerated ' + descriptor_file_name


	@staticmethod
	def display_descriptor_contents(simple_descriptor_path, simple_descriptor_content):
		print '   Source: ' + simple_descriptor_content.get('discovery-registry')
		print 'Providers: ' + simple_descriptor_content.get('provider-config-ref')
		print '  Cluster: ' + simple_descriptor_content.get('cluster')
		print ' Services:'
		for s in simple_descriptor_content.get('services'):
			service_name = s.get('name')
			if (s.has_key('url')):				
				print '\t' + service_name + ' (' + s.get('url') + ')'
			else:
				print '\t' + service_name + ' (discover)'

	@staticmethod
	def display_discovered_service_urls(service_urls):
		for service in service_urls:
			print '{:15} : {}'.format(service[0], service[1])

