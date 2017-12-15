# knox-topology-gen

__*This concept has been incorporated into Apache Knox 0.14.0. While you may still find value in the details presented, Knox provides this functionality (and more).*__


This project provides an example of using the [Apache™ Ambari](https://ambari.apache.org) [REST API](https://github.com/apache/ambari/blob/trunk/ambari-server/docs/api/v1/index.md) to populate [Apache™ Knox](http://knox.apache.org) topology descriptors.

To try it out, you'll need an [Apache™ Hadoop®](http://hadoop.apache.org) cluster managed by Ambari. You can create one using [VirtualBox](https://www.virtualbox.org) and [Vagrant](https://www.vagrantup.com) by following the instructions in the [Ambari Quick Start Guide](https://cwiki.apache.org/confluence/display/AMBARI/Quick+Start+Guide)

Once you have access to an Ambari instance, you can edit __resources/demo.yml__ (specify the Ambari host, and the cluster name) and __test_build_topology.py__ (edit the credentials).
Then, run __test_build_topology.py__, which will generate __demo.xml__ (a deployable Knox topology)

All the REST API interactions can be found in __topologydiscovery.py__, and the Knox topology assembly is done in __topologybuilder.py__.

This project uses [YAML](http://yaml.org) descriptors as input to determine the content of the resulting topology, and these descriptors reference provider configuration XML files (which are copied into the resulting topology file).

