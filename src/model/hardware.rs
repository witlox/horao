//! Datacenter hardware (compute & storage)
//!
//! This module contains the definition of compute/storage equipment (hardware) and their properties.
//! We assume that 'faulty' equipment state is either up or down, it should be handled in a state machine, not here.
//! Also we assume that these data structures are not very prone to change, given that this implies a manual activity.

use crate::model::status::DeviceStatus;

pub struct DataCenter {
    name: String,
    number: i64,
    rows: Vec<Row>
}

pub struct Row {
    name: String,
    number: i64,
    cabinets: Vec<Cabinet>
}

pub struct Cabinet {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    servers: Vec<Server>,
    chassis: Vec<Chassis>
}

pub struct Chassis {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    servers: Vec<Server>
}

pub struct Server {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    cpu: Vec<CPU>,
    ram: Vec<RAM>,
    disk: Vec<Disk>,
    nic: Vec<NIC>,
    accelerator: Vec<Accelorator>,
    status: DeviceStatus
}

pub struct RAM {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    size_gb: i64,
    speed_mhz: i64,
    usage_gb: i64
}

pub struct NIC {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    mac: String,
    link_status: DeviceStatus,
    port_speed_gbps: i64,
    number_of_ports: i64
}

pub struct CPU {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    clock_speed: i64,
    cores: i64,
    features: String
}

pub struct Accelorator {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    memory_gb: i64,
    chip: String,
    clock_speed: i64
}

pub struct Disk {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    size_gb: i64,
    usage_gb: i64
}
