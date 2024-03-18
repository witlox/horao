//! [`OSI`] layers
//!
//! This module contains the definition of networking activities and their properties.
//! We assume that these data structures are prone to change, given that these are configuration artifacts.
//!
//!  [`OSI`]: https://en.wikipedia.org/wiki/OSI_model

use serde::{Serialize, Deserialize};

use crate::model::status::DeviceStatus;


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Port {
    serial_number: String,
    name: String,
    model: String,
    number: i64,
    mac: String,
    status: DeviceStatus,
    speed_gb: i64,
}

impl Port {
    pub fn is_up(&self) -> bool {
        self.status.is_up()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Link {
    left: Port,
    right: Port,
}

impl Link {
    pub fn is_up(&self) -> bool {
        self.left.is_up() && self.right.is_up()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LinkLayer {
    Layer2,
    Layer3,
}

#[derive(Debug, Serialize, Deserialize)]
pub enum Protocol {
    TCP,
    UDP,
    ICMP,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct IpAddress {
    address: String,
    netmask: String,
    gateway: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Route {
    destination: IpAddress,
    gateway: IpAddress,
    metric: i64,
}


#[derive(Debug, Serialize, Deserialize)]
pub struct FirewallRule {
    name: String,
    action: String,
    source: IpAddress,
    destination: IpAddress,
    protocol: Protocol,
    port: i64,
}
