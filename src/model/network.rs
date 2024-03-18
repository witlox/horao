pub enum NetworkTopology {
    Tree,
    VL2,
    AlFares,
    Portland,
    Hedera,
    DCell,
    BCube,
    MDCube,
    FiConn,
    OSA,
    cThrough,
    Helios,
    DragonFly
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
    Down,
    Degraded
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
    Down,
    Degraded
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
    Down,
    Degraded
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
    Down,
    Degraded
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
