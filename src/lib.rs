///
/// Library containing the entrypoint for all logic.
/// The executable is a wrapper around the library functions.
///
#[macro_use]
extern crate lazy_static;

mod settings;
use settings::Settings;


lazy_static! {
    pub static ref CONFIG: Settings = match Settings::new() {
        Ok(cfg) => cfg,
        Err(error) => panic!("failure in loading settings {:?}", error),
    };
}

/// Simple function to add two ints
///
/// # Arguments
///
/// * `a` - left integer to add to right
/// * `b` - right integer to add to left
///
/// # Examples
///
/// add_two(1, 2)
///
/// ```
/// let r = liblimen::add_two(3, 4);
/// assert_eq!(r, 7);
/// ```
pub fn add_two(a: i32, b: i32) -> i32 {
    return a + b;
}

