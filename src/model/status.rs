//! States that we are able to manage

use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DeviceStatus {
    Up,
    Down
}

impl DeviceStatus {
    pub fn is_up(&self) -> bool {
        match self {
            DeviceStatus::Up => true,
            _ => false
        }
    }
}
