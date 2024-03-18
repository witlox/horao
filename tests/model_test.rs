mod common;

use libhorao::model::network;

#[test]
fn topology_traversal_works() {
    let dcn = network::DataCenterNetwork::new("name".to_string(), network::NetworkType::Management, vec![], vec![], vec![]);
    assert_eq!(network::NetworkTopology::Undefined, dcn.get_topology());
}
