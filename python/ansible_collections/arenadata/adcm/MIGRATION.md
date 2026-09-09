# ADCM Ansible Collection - FQCN Migration Guide

## Overview

The ADCM Ansible plugins have been converted to a proper Ansible Collection structure with FQCN (Fully Qualified Collection Name).

## Collection Details

- **Namespace**: `arenadata`
- **Collection Name**: `adcm`
- **FQCN Prefix**: `arenadata.adcm`

## Plugin Mapping

### Action Plugins

| Old Name (Short)         | New FQCN                              |
|--------------------------|---------------------------------------|
| `adcm_add_host`          | `arenadata.adcm.adcm_add_host`        |
| `adcm_add_host_to_cluster` | `arenadata.adcm.adcm_add_host_to_cluster` |
| `adcm_change_flag`       | `arenadata.adcm.adcm_change_flag`     |
| `adcm_change_maintenance_mode` | `arenadata.adcm.adcm_change_maintenance_mode` |
| `adcm_check`             | `arenadata.adcm.adcm_check`           |
| `adcm_config`            | `arenadata.adcm.adcm_config`          |
| `adcm_custom_log`        | `arenadata.adcm.adcm_custom_log`      |
| `adcm_delete_host`       | `arenadata.adcm.adcm_delete_host`     |
| `adcm_delete_service`    | `arenadata.adcm.adcm_delete_service`  |
| `adcm_hc`                | `arenadata.adcm.adcm_hc`              |
| `adcm_manage_revision`   | `arenadata.adcm.adcm_manage_revision` |
| `adcm_multi_state_set`   | `arenadata.adcm.adcm_multi_state_set` |
| `adcm_multi_state_unset` | `arenadata.adcm.adcm_multi_state_unset` |
| `adcm_remove_host_from_cluster` | `arenadata.adcm.adcm_remove_host_from_cluster` |
| `adcm_state`             | `arenadata.adcm.adcm_state`           |

### Lookup Plugins

| Old Name (Short)         | New FQCN                              |
|--------------------------|---------------------------------------|
| `adcm_config`            | `arenadata.adcm.adcm_config`          |
| `adcm_state`             | `arenadata.adcm.adcm_state`           |

## Usage Examples

### Before (Legacy)

```yaml
- name: Check something
  adcm_check:
    title: "Check"
    msg: "This is message"
    result: yes

- name: Set host state
  debug: msg="set host state {{ lookup('adcm_state', 'host', 'configured') }}"
```

### After (FQCN)

```yaml
- name: Check something
  arenadata.adcm.adcm_check:
    title: "Check"
    msg: "This is message"
    result: yes

- name: Set host state
  debug: msg="set host state {{ lookup('arenadata.adcm.adcm_state', 'host', 'configured') }}"
```

## Collection Structure

```
python/ansible_collections/arenadata/adcm/
├── galaxy.yml                           # Collection metadata
├── README.md                            # Collection documentation
├── __init__.py
└── plugins/
    ├── __init__.py
    ├── action/                          # Action plugins
    │   ├── __init__.py
    │   ├── adcm_add_host.py
    │   ├── adcm_add_host_to_cluster.py
    │   ├── adcm_change_flag.py
    │   ├── adcm_change_maintenance_mode.py
    │   ├── adcm_check.py
    │   ├── adcm_config.py
    │   ├── adcm_custom_log.py
    │   ├── adcm_delete_host.py
    │   ├── adcm_delete_service.py
    │   ├── adcm_hc.py
    │   ├── adcm_manage_revision.py
    │   ├── adcm_multi_state_set.py
    │   ├── adcm_multi_state_unset.py
    │   ├── adcm_remove_host_from_cluster.py
    │   └── adcm_state.py
    └── lookup/                          # Lookup plugins
        ├── __init__.py
        ├── adcm_config.py
        └── adcm_state.py
```

## Installation

The collection is installed by copying to the Ansible collections path:

```bash
# In Dockerfile
COPY python/ansible_collections/arenadata/adcm /root/.ansible/collections/ansible_collections/arenadata/adcm
```

## Backward Compatibility

The old plugin path (`python/ansible_share/plugins`) is kept for backward compatibility. Both legacy and FQCN names will work during the transition period.

## Benefits of FQCN

1. **Uniqueness**: No naming conflicts with other collections
2. **Discoverability**: Easy to identify the source of plugins
3. **Versioning**: Collections can be versioned independently
4. **Distribution**: Can be published to Ansible Galaxy
5. **Best Practices**: Follows Ansible modern standards
