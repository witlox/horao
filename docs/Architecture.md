# Architecture Documentation

There are 2 levels of abstraction in the architecture of HORAO:
1. The high-level architecture which describes rough overall state of a 'logical infrastructure'. 
A logical infrastructure is a logical aggregation of lower level resources for potentially multiple datacenters.
With this logical infrastructure, one should be able to schedule resource and/or maintenance claims for resource profiles.
These resource profiles describe the desired resources on a course-grained level.
2. The low-level architecture which describes the actual resources that are available in a datacenter. 
These resources are the actual physical or virtual resources that are available in a datacenter.
These resources are managed by (a) datacenter manager(s) and should ideally be updated dynamically.
The intent is that there are 3 rough dimension of any given datacenter; network, storage and compute.

# Distribution pattern
In order to aggregate the lower level resources into a logical infrastructure, we assume that any
instance of HORAO will have all information eventually. We will leverage CRDTs to ensure consistency
across all instances of HORAO. For the data center resources we will use fractionally-indexed arrays,
for the logical infrastructure we will use a Multi-Value Map.

## Synchronization and backup
Because of the nature of the design, split-brain situations should not exist. 
We will synchronize state via a gossip protocol (over websockets in starlette).
Persistent storage will be provided by a key-value database (Redis).

# Design assumptions

## Reasonably 'static' resources

There are various resources that are relatively static, such as physical devices. These resources are usually created once and then used for a long time. The management of these resources is usually done by a small group of people, and the changes are relatively infrequent.

## Reasonably 'dynamic' resources

There are various resources that are relatively dynamic, such as virtual machines. These resources are usually created and destroyed frequently, and the management of these resources is usually done by a large group of people.
