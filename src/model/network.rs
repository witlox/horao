//! Networking equipment
//!
//! This module contains the definition of networking equipment (hardware) and their properties.
//! We assume that 'faulty' equipment state is either up or down, it should be handled in the state machine, not here.

pub enum NetworkTopology {
    Tree, // (low-radix) tree topology, or star-bus topology, in which star networks are interconnected via bus networks
    VL2, // (low-radix, clos) scales to support huge data centers with uniform high capacity between servers, performance isolation between services, and Ethernet layer-2 semantics
    AlFares, // (high-radix, fat-tree) provides a scalable and cost-effective interconnection of servers in modern data centers, interconnecting commodity switches in a fat-tree architecture achieves the full bisection bandwidth of clusters
    Portland, // (high-radix, fat-tree) scalable, fault tolerant layer 2 routing and forwarding protocol for data center environments
    Hedera, // (high-radix, fat-tree) dynamic flow scheduling system that adaptively schedules a multi-stage switching fabric to efficiently utilize aggregate network resources
    DCell, // (low-radix, recursive) a recursively defined structure, in which a high-level DCell is constructed from many low-level DCells and DCells at the same level are fully connected with one another
    BCube, // (low-radix, recursive) a new network architecture specifically designed for shipping-container based, modular data centers
    MDCube, // (low-radix, recursive) a high performance interconnection structure to scale BCube-based containers to mega-data centers
    FiConn, // (low-radix, recursive) utilizes both ports and only the low-end commodity switches to form a scalable and highly effective structure
    OSA, // (low-radix, flexible, fully optical) leverage runtime reconfigurable optical devices to dynamically changes its topology and link capacities to adapt to dynamic traffic patterns
    cThrough, // (low-radix, flexible, hybrid) responsibility for traffic demand estimation and traffic demultiplexing resides in end hosts, making it compatible with existing packet switches
    Helios, // (low-radix, flexible, hybrid) hybrid electrical/optical switch architecture that can deliver significant reductions in the number of switching elements, cabling, cost, and power consumption
    DragonFly1D, // (high-radix, dragonfly) completely connected router groups, each pair of router groups has one or multiple global optical connection, each pair of routers in the same router group has a single local connection
    Slingshot2D, // (high-radix, dragonfly) enhanced 1D, replaces the router group with a flattened butterfly 2D connected group, where every two groups can be connected by one or multiple global connections
    DragonFlyPlus // (high-radix, dragonfly) enhanced 1D, each router group contains two sub-groups of switches: leaf switches or spine switches. Spine switches are directly connected to spines of the other router groups, leaf switches are connected to the spine switches in the same group
}

pub enum NetworkType {
    management,
    control,
    data
}

pub struct DataCenterNetwork {
    name: String,
    type: NetworkType,
    switches: Vec<Switch>,
    routers: Vec<Router>,
    firewalls: Vec<Firewall>,
    topology: NetworkTopology
}

pub enum FirewallStatus {
    Up,
    Down
}

pub struct Firewall {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    status: FirewallStatus,
    lan_ports: Vec<Port>,
    wan_ports: Vec<Port>
}

pub enum RouterType {
    Core,
    Edge
}

pub enum RouterStatus {
    Up,
    Down
}

pub struct Router {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    type: RouterType,
    status: RouterStatus,
    lan_ports: Vec<Port>,
    wan_ports: Vec<Port>
}

pub enum LinkLayer {
    Layer2,
    Layer3
}

pub enum SwitchType {
    Access,
    Distribution,
    Core
}

pub enum SwitchStatus {
    Up,
    Down
}

pub enum SwitchManagement {
    Managed,
    Unmanaged
}

pub struct Switch {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    layer: LinkLayer,
    type: SwitchType,
    status: SwitchStatus,
    management: SwitchManagement,
    lan_ports: Vec<Port>,
    uplink_ports: Vec<Port>
}

pub enum LinkStatus {
    Up,
    Down
}

pub struct Port {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    mac: String,
    status: LinkStatus,
    speed_gb: i64
}
