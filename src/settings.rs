//! Configration File handles and settings
//! We allow for multiple configuration files in the configuration directory.
//! Each file represents a given runtime environment:
//! Default.toml loads our defaults.
//! Development.toml overrides the settings from default when on a development environment (e.g. local)
//! Testing.toml overrides the settings from default in regards to integration testing.
//! Production.toml overrides any production specific settings.

extern crate dirs;

use config::{ Config, ConfigError, Environment, File };
use serde::Deserialize;
use std::path::PathBuf;
use std::env;

/// Standard search locations for configuration files
static SYS_CONF_DIR: &str = "/etc/horao";
fn get_usr_conf_dir () -> Option<PathBuf> {
    match dirs::home_dir() {
        Some(p) => {
            let mut lp: PathBuf = p;
            lp.push(".config");
            lp.push("horao");
            Some(lp)
        },
        None => None
    }
}

/// Items that can be defined in our Settings
#[derive(Debug, Deserialize)]
#[allow(unused)]
pub struct Log {
    pub level: String,
}

#[derive(Debug, Deserialize)]
#[allow(unused)]
pub struct Gossip {
    pub protocol: String,
}

#[derive(Debug, Deserialize)]
#[allow(unused)]
pub struct Settings {
    log: Log,
    gossip: Gossip,
}

/// Settings loader
impl Settings {
    pub fn new() -> Result<Self, ConfigError> {
        let run_mode = env::var("RUN_MODE").unwrap_or_else(|_| "development".into());
        let mut b = Config::builder();
        // system configuration path
        b = b.add_source(File::with_name(&format!("{}/default", SYS_CONF_DIR)).required(false))
             .add_source(File::with_name(&format!("{}/{}", SYS_CONF_DIR, run_mode)).required(false));
        // user configuration path
        if get_usr_conf_dir().is_some() {
            b = b.add_source(File::with_name(&format!("{}/default", get_usr_conf_dir().unwrap().canonicalize().unwrap().to_str().unwrap())).required(false))
                 .add_source(File::with_name(&format!("{}/{}", get_usr_conf_dir().unwrap().canonicalize().unwrap().to_str().unwrap(), run_mode)).required(false))
        }
        // environment variables PREFIX 'LIMEN_'
        b = b.add_source(Environment::with_prefix("HORAO"));
        b.build()?.try_deserialize()
    }
}
