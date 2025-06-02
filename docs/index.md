# Management engine for hybrid multi-cloud environments

The goal of `HORAO` is to be able to manage tenants across various hybrid multi-cloud environments. The engine is designed to be able to manage resources across various cloud providers, such as AWS, Azure, and GCP as well as on-prem with engines like [OCHAMI](https://www.ochami.org).
One of the key design features is to provide a model-based approach to managing resources, which allows for a high level of abstraction and automation.
`HORAO` will be able to check the current allocation state of the distributed resources, and users will be able to create reservations based on time and availability.
Secondary, site administrators will be able to plan maintenance events, to validate what the impact of a maintenance event will be on the tenants. 


These pages are currently available:
- [Architecture](./Architecture.md)
- [Development notes](./Development.md)
- [Creating a virtual environment](./CreateVirtualEnv.md)
- [Authentication](./Authentication.md)
- [Controllers](./Controllers.md)
- [Telemetry](./Telemetry.md)
- [Research](./Research.md)
