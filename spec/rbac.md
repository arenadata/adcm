# ADCM and Django RBAC

## Django permission model

Django creates (by default) 4 permission per each model.

 * view
 * create
 * update
 * delete
 
For example, for **Cluster** model will be created 4 permissions with codenames:

 * view_cluster
 * add_cluster
 * change_cluster
 * delete_cluster

Permissions can be added to any user or any user group. 

## ADCM REST API

In ADCM api Django permissions are checked for every view. Model name is obtained from the **queryset** field of view class.

### User management

All user permissions and groups now can be viewed in API:

```GET /api/v1/user/joe/```

```json
{
    "change_group": "http://localhost:8000/api/v1/user/joe/group/",
    "change_password": "http://localhost:8000/api/v1/user/joe/password/",
    "change_permission": "http://localhost:8000/api/v1/user/joe/permission/",
    "groups": [
        {
            "change_permission": "http://localhost:8000/api/v1/group/admin/permission/",
            "name": "admin",
            "url": "http://localhost:8000/api/v1/group/admin/"
        }
    ],
    "is_superuser": false,
    "url": "http://localhost:8000/api/v1/user/joe/",
    "user_permissions": [
        {
            "app_label": "cm",
            "codename": "change_cluster",
            "model": "cluster",
            "name": "Can change cluster"
        },
        {
            "app_label": "cm",
            "codename": "view_cluster",
            "model": "cluster",
            "name": "Can view cluster"
        },
        {
            "app_label": "cm",
            "codename": "view_hostprovider",
            "model": "hostprovider",
            "name": "Can view host provider"
        }
    ],
    "username": "joe"
}
```

Add permission to user:

```POST /api/v1/user/joe/permission/ codename=change_cluster```

Remove permission from user:

```DELETE /api/v1/user/joe/permission/ codename=change_cluster```

Add user to group: 

```POST /api/v1/user/joe/group/ name=admin```

Remove user from group:

```DELETE /api/v1/user/joe/group/ name=admin```

User can be created with ```is_superuser=true``` flag. Super user bypass permissions system altogether. By default all users are created as superuser.

### Group management

Create group:

```POST /api/v1/group/ name=dba```

Delete group

```DELETE /api/v1/group/dba/```

View group:

```GET /api/v1/group/dba/```

```json
{
    "change_permission": "http://localhost:8000/api/v1/group/dba/permission/",
    "name": "dba",
    "permissions": [
        {
            "app_label": "cm",
            "codename": "view_host",
            "model": "host",
            "name": "Can view host"
        }
    ],
    "url": "http://localhost:8000/api/v1/group/dba/"
}
```

Add permission to group:

```POST /api/v1/group/dba/permission/ codename=change_cluster```

Remove permission from group:

```DELETE /api/v1/group/dba/permission/ codename=change_cluster```






