# Architecture Documentation

There are 2 levels of abstraction in the architecture of `HORAO`:
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
instance of `HORAO` will have all information eventually. We will leverage CRDTs to ensure consistency
across all instances of `HORAO`. The main CRDT datastructure we leverage is Last-Writer-Wins Map (LWWMap).
The LWWMap internally uses Last-Writer-Wins register (LWWRegister) to ensure consistent key-value pairs.
The internal synchronization mechanism of the CRDTs is based on a Lamport Logical Clock, this clock uses
a vector based on unix timestamps to ensure that the order of operations is consistent across all instances.
When running multiple instances of `HORAO` we will synchronize the state of the CRDTs using the API.
Because we are using an actual clock, it is important to ensure that the clocks are synchronized across all instances.
We recommend to use NTP to synchronize the clocks, and if needed one can set an allowed clock-offset.

## Synchronization and backup
Because of the nature of the design, split-brain situations should not exist. 
We will synchronize state via the `HORAO` API (over websockets in starlette).
Persistent storage will be provided by a key-value database (Redis).
The synchronization mechanism used by the CRDTs is based on a Lamport Logical Clock, using a vector based on unix timestamps.
Due to the nature of this, we may want to allow for a 'small' clock-skew.
This can be configured in the `.env` file as follows:
```dotenv
CLOCK_OFFSET: 0.0 #float, default=0.0; set the allowed clock offset for synchronization
```

### Backpressure and timing
The formula for synchronizing state is `t > now - t' OR s > max` where `t` is the configured delta, `now` is the current time and `t'` is the time since the last synchronization, `s` is the count of changes on the stack and `max` is the stack count threshold.
If the formula evaluates to true, the state is synchronized and counters are reset to zero.
The following environment variables in the .env file are used to configure the synchronization:
```dotenv
SYNC_DELTA=180  #integer, default=180; time delta in seconds
SYNC_MAX=1000 #integer, default=1000; number of changes since last sync
```

# Design assumptions

## Reasonably 'static' resources

There are various resources that are relatively static, such as physical devices. These resources are usually created once and then used for a long time. The management of these resources is usually done by a small group of people, and the changes are relatively infrequent.

## Reasonably 'dynamic' resources

There are various resources that are relatively dynamic, such as virtual machines. These resources are usually created and destroyed frequently, and the management of these resources is usually done by a large group of people.
