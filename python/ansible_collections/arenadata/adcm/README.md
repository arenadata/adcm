# Arenadata ADCM Ansible Collection

Ansible Collection for ADCM (Arenadata Cluster Manager) - a cluster management platform.

## Description

This collection provides Ansible plugins for managing clusters, services, and hosts through ADCM.

## Plugins

### Action Plugins

- `adcm_add_host` - Add Host
- `adcm_add_host_to_cluster` - Add existing host to cluster
- `adcm_change_flag` - Raise or Lower flags on Cluster, Service, Component, Provider or Host
- `adcm_change_maintenance_mode` - Change Host, Service or Component maintenance mode
- `adcm_check` - Log check results to structured JSON log storage
- `adcm_config` - Change config values in runtime
- `adcm_custom_log` - Add entries to log storage
- `adcm_delete_host` - Delete Host
- `adcm_delete_service` - Delete service from cluster
- `adcm_hc` - Change host component map for cluster
- `adcm_manage_revision` - Manage configuration revisions
- `adcm_multi_state_set` - Add state to multi_state field
- `adcm_multi_state_unset` - Remove state from multi_state field
- `adcm_remove_host_from_cluster` - Remove host from cluster
- `adcm_state` - Change state of object

### Lookup Plugins

- `adcm_config` - Set config key for host, cluster or service
- `adcm_state` - Update state for host, cluster or service

## Usage

After installation, use the FQCN (Fully Qualified Collection Name) to reference plugins:

```yaml
- name: Check something
  arenadata.adcm.adcm_check:
    title: "Check"
    msg: "This is message"
    result: yes

- name: Set host state
  debug: msg="set host state {{ lookup('arenadata.adcm.adcm_state', 'host', 'configured') }}"
```

## License

Apache-2.0

## Author

Arenadata Team
