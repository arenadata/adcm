import { Component, Type, ViewChild } from '@angular/core';
import { IColumns } from '@app/adwp';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { Store } from '@ngrx/store';

import { TypeName } from '@app/core/types';
import { RbacPolicyModel } from '@app/models/rbac/rbac-policy.model';
import { RbacEntityListDirective } from '@app/abstract-directives/rbac-entity-list.directive';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { RbacPolicyService } from '@app/services/rbac-policy.service';
import { ADD_SERVICE_PROVIDER } from '../../shared/add-component/add-service-model';
import { AddButtonComponent } from '../../shared/add-component';
import { RbacPolicyFormComponent } from '../../components/rbac/policy-form/rbac-policy-form.component';
import { RbacRoleModel } from '../../models/rbac/rbac-role.model';
import { RbacUserModel } from '../../models/rbac/rbac-user.model';
import { RbacGroupModel } from '../../models/rbac/rbac-group.model';

@Component({
  selector: 'app-policies',
  templateUrl: './policies.component.html',
  styleUrls: ['./policies.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: RbacPolicyService }
  ],
})
export class PoliciesComponent extends RbacEntityListDirective<RbacPolicyModel> {
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
      label: 'Policy name',
      sort: 'name',
      value: (row) => row.name,
    },
    {
      label: 'Description',
      value: (row) => row.description,
    },
    {
      label: 'Role',
      value: (row) => (row.role && (row.role as any as RbacRoleModel).display_name) ?? '',
    },
    {
      label: 'Users',
      value: (row) => row.user.map((user: RbacUserModel) => user.username).join(', '),
      className: 'one-line-string',
    },
    {
      label: 'Groups',
      value: (row) => row.group.map((group: RbacGroupModel) => group.name).join(', '),
      className: 'one-line-string',
    },
    {
      label: 'Objects',
      value: (row) => row.object.map((object: any) => object.name).join(', '),
      className: 'one-line-string',
    },
  ] as IColumns<RbacPolicyModel>;

  type: TypeName = 'policy';

  component: Type<RbacPolicyFormComponent> = RbacPolicyFormComponent;

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected entityService: RbacPolicyService,
  ) {
    super(service, store, route, router, dialog, entityService);
  }

  getTitle(row: RbacPolicyModel): string {
    return row.name;
  }

}
