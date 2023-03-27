import { Component, Type, ViewChild } from '@angular/core';
import { IColumns } from '@app/adwp';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { Store } from '@ngrx/store';
import { RbacGroupModel } from '@app/models/rbac/rbac-group.model';
import { TypeName } from '../../core/types';
import { ADD_SERVICE_PROVIDER } from '../../shared/add-component/add-service-model';
import { AddButtonComponent, BaseFormDirective } from '../../shared/add-component';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { RbacEntityListDirective } from '@app/abstract-directives/rbac-entity-list.directive';
import { RbacGroupService } from '../../services/rbac-group.service';
import { RbacGroupFormComponent } from '../../components/rbac/group-form/rbac-group-form.component';

const userNameMapper = (group: RbacGroupModel) => {
  return group.user.map((u) => u.username).join(', ');
};

@Component({
  selector: 'app-groups',
  templateUrl: './groups.component.html',
  styleUrls: ['./groups.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: RbacGroupService }
  ],
})
export class GroupsComponent extends RbacEntityListDirective<RbacGroupModel> {
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
      label: 'Group name',
      sort: 'name',
      value: (row) => row.name,
    },
    {
      label: 'Description',
      sort: 'description',
      value: (row) => row.description,
    },
    {
      label: 'Users',
      className: 'one-line-string',
      value: userNameMapper,
    },
    {
      label: 'Type',
      sort: 'type',
      value: (row) => row.type,
    }
  ] as IColumns<RbacGroupModel>;

  type: TypeName = 'group';

  component: Type<BaseFormDirective> = RbacGroupFormComponent;

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected entityService: RbacGroupService,
  ) {
    super(service, store, route, router, dialog, entityService);
  }

  getTitle(row: RbacGroupModel): string {
    return row.name;
  }

}
