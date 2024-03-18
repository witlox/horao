# HORAO: management engine for hybrid multi-cloud environments

There are various cloud based management engines available. These tend to be either very specific to a certain cloud provider, or very generic and complex. The goal of HORAO is to provide a simple, yet powerful, management engine that can be used to manage hybrid multi-cloud environments. One of the key design features is to provide a model-based approach to managing resources, which allows for a high level of abstraction and automation.

# Design assumptions

## Reasonably 'static' resources

There are various resources that are relatively static, such as physical devices. These resources are usually created once and then used for a long time. The management of these resources is usually done by a small group of people, and the changes are relatively infrequent.

## Reasonably 'dynamic' resources

There are various resources that are relatively dynamic, such as virtual machines. These resources are usually created and destroyed frequently, and the management of these resources is usually done by a large group of people.

## Configuration file

We look for a configuration file in the following spots (and again the lower the number in this list, the higher the precedence):

1. custom: as a parameter passed to the application (--config)
2. user: ~/.config/horao/config.yaml
3. system: /etc/horao/config.yaml

**_Note_** if partial information exists in multiple files the precedence defines which value is actually chosen.
