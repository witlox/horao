//! Networking equipment
//!
//! This module contains the definition of networking equipment (hardware) and their properties.
//! We assume that 'faulty' equipment state is either up or down, it should be handled in the state machine, not here.
//! Also we assume that these data structures are not very prone to change, given that this implies a manual activity.

use serde::{Serialize, Deserialize};

use crate::model::status::DeviceStatus;
use crate::model::osi_layers::LinkLayer;
use crate::model::osi_layers::Port;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum NetworkTopology {
    Tree, // (low-radix) tree topology, or star-bus topology, in which star networks are interconnected via bus networks
    VL2, // (low-radix, clos) scales to support huge data centers with uniform high capacity between servers, performance isolation between services, and Ethernet layer-2 semantics
    FatTree, // (high-radix, clos, AlFares) provides a scalable and cost-effective interconnection of servers in modern data centers, interconnecting commodity switches in a fat-tree architecture achieves the full bisection bandwidth of clusters
    Portland, // (high-radix, fat-tree) scalable, fault tolerant layer 2 routing and forwarding protocol for data center environments
    Hedera, // (high-radix, fat-tree) dynamic flow scheduling system that adaptively schedules a multi-stage switching fabric to efficiently utilize aggregate network resources
    DCell, // (low-radix, recursive) a recursively defined structure, in which a high-level DCell is constructed from many low-level DCells and DCells at the same level are fully connected with one another
    BCube, // (low-radix, recursive) a new network architecture specifically designed for shipping-container based, modular data centers
    MDCube, // (low-radix, recursive) a high performance interconnection structure to scale BCube-based containers to mega-data centers
    FiConn, // (low-radix, recursive) utilizes both ports and only the low-end commodity switches to form a scalable and highly effective structure
    OSA, // (low-radix, flexible, fully optical) leverage runtime reconfigurable optical devices to dynamically changes its topology and link capacities to adapt to dynamic traffic patterns
    CThrough, // (low-radix, flexible, hybrid) responsibility for traffic demand estimation and traffic demultiplexing resides in end hosts, making it compatible with existing packet switches
    Helios, // (low-radix, flexible, hybrid) hybrid electrical/optical switch architecture that can deliver significant reductions in the number of switching elements, cabling, cost, and power consumption
    DragonFly, // (high-radix, dragonfly) completely connected router groups, each pair of router groups has one or multiple global optical connection, each pair of routers in the same router group has a single local connection
    Slingshot, // (high-radix, dragonfly) enhanced DragonFly (1D), replaces the router group with a flattened butterfly 2D connected group, where every two groups can be connected by one or multiple global connections
    DragonFlyPlus, // (high-radix, dragonfly) enhanced DragonFly (1D), each router group contains two sub-groups of switches: leaf switches or spine switches. Spine switches are directly connected to spines of the other router groups, leaf switches are connected to the spine switches in the same group
    Undefined
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NetworkType {
    Management, // administrative access to devices, analysis of state, health and configuration
    Control, // formulates and distributes guidance to the data plane, overseeing orchestration and coordination
    Data // aka forwarding plane, policies, scaling and/or behavior triggers are generally executed here
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataCenterNetwork {
    name: String,
    network_type: NetworkType,
    switches: Vec<Switch>,
    routers: Vec<Router>,
    firewalls: Vec<Firewall>,
    topology: NetworkTopology
}

impl DataCenterNetwork {
    pub fn new(name: String, network_type: NetworkType, switches: Vec<Switch>, routers: Vec<Router>, firewalls: Vec<Firewall>) -> DataCenterNetwork {
        DataCenterNetwork {
            name,
            network_type,
            switches,
            routers,
            firewalls,
            topology: NetworkTopology::Undefined
        }
    }
    pub fn get_topology(&self) -> NetworkTopology {
        resolve_network_topo(self.switches.clone())
    }
}

/// Resolve the network topology based on the way the switches are connected
///
/// # Arguments
///
/// * `switches` - Vector of all switches in the network
///
/// # Examples
///
/// let switches = vec![Switch::new("1", "s1", "cisco", 1, LinkLayer::Ethernet, SwitchType::Access, DeviceStatus::Up, true, vec![], vec![])];
/// resolve_network_topo(switches)
///
/// ```
/// use libhorao::model::network::{Switch, NetworkTopology, SwitchType, resolve_network_topo};
/// use libhorao::model::osi_layers;
/// use libhorao::model::status;
///
/// let switches = vec![Switch::new("1".to_string(), "s1".to_string(), "cisco".to_string(), 1, osi_layers::LinkLayer::Layer3, SwitchType::Access, status::DeviceStatus::Up, true, vec![], vec![])];
/// assert_eq!(NetworkTopology::Undefined, resolve_network_topo(switches))
/// ```
pub fn resolve_network_topo(switches: Vec<Switch>) -> NetworkTopology {
    NetworkTopology::Undefined
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Firewall {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    status: DeviceStatus,
    lan_ports: Vec<Port>,
    wan_ports: Vec<Port>
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RouterType {
    Core,
    Edge
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Router {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    router_type: RouterType,
    status: DeviceStatus,
    lan_ports: Vec<Port>,
    wan_ports: Vec<Port>
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SwitchType {
    Access,
    Distribution, // also know as Aggregation
    Core
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Switch {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    layer: LinkLayer,
    switch_type: SwitchType,
    status: DeviceStatus,
    managed: bool,
    lan_ports: Vec<Port>,
    uplink_ports: Vec<Port>
}

impl Switch {
    pub fn new(serial_number: String, name: String, model: String, number: i64, layer: LinkLayer, switch_type: SwitchType, status: DeviceStatus, managed: bool, lan_ports: Vec<Port>, uplink_ports: Vec<Port>) -> Switch {
        Switch {
            serial_number,
            name,
            model,
            number,
            layer,
            switch_type,
            status,
            managed,
            lan_ports,
            uplink_ports
        }
    }
}
