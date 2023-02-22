import { Component, Type, ViewChild } from '@angular/core';
import { IColumns } from '@app/adwp';
import { Store } from '@ngrx/store';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';

import { TypeName } from '@app/core/types';
import { RbacRoleModel } from '@app/models/rbac/rbac-role.model';
import { RbacEntityListDirective } from '@app/abstract-directives/rbac-entity-list.directive';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { RbacRoleService } from '@app/services/rbac-role.service';
import { ADD_SERVICE_PROVIDER } from '../../shared/add-component/add-service-model';
import { AddButtonComponent } from '../../shared/add-component';
import { RbacRoleFormComponent } from '../../components/rbac/role-form/rbac-role-form.component';

const permissionNameMapper = (role: RbacRoleModel) => {
  return role.child.map((u) => u.name).join(', ');
};


@Component({
  selector: 'app-roles',
  templateUrl: './roles.component.html',
  styleUrls: ['./roles.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: RbacRoleService }
  ],
})
export class RolesComponent extends RbacEntityListDirective<RbacRoleModel> {
  @ViewChild(AddButtonComponent) addButton: AddButtonComponent;

  listColumns = [
    {
      type: 'choice',
      modelKey: 'checked',
      className: 'choice-column',
      headerClassName: 'choice-column',
      disabled: (row) => row.built_in,
    },
    {
      label: 'Role name',
      sort: 'display_name',
      value: (row) => row.display_name,
    },
    {
      label: 'Description',
      sort: 'description',
      value: (row) => row.description,
    },
    {
      label: 'Permissions',
      className: 'one-line-string',
      value: permissionNameMapper,
    }
  ] as IColumns<RbacRoleModel>;

  type: TypeName = 'role';

  component: Type<RbacRoleFormComponent> = RbacRoleFormComponent;

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected entityService: RbacRoleService,
  ) {
    super(service, store, route, router, dialog, entityService);
  }

  getTitle(row: RbacRoleModel): string {
    return row.name;
  }

}
