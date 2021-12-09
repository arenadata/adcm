import { Component, ViewChild } from '@angular/core';
import { IColumns, RowEventData } from '@adwp-ui/widgets';
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
    },
    {
      label: 'Role name',
      sort: 'name',
      value: (row) => row.name,
    },
    {
      label: 'Description',
      sort: 'description',
      value: (row) => row.description,
    },
  ] as IColumns<RbacRoleModel>;

  type: TypeName = 'rbac_role';

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

  clickRow(data: RowEventData): void {
    this.showForm(data);
  }

  getTitle(row: RbacRoleModel): string {
    return row.name;
  }

  showForm(data: RowEventData): void {
    this.addButton.showForm(this.entityService.model(data.row));
  }

}
