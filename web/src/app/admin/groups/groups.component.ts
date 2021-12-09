import { Component, ViewChild } from '@angular/core';
import { IColumns, RowEventData } from '@adwp-ui/widgets';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { Store } from '@ngrx/store';
import { RbacGroupModel } from '@app/models/rbac/rbac-group.model';
import { TypeName } from '../../core/types';
import { RbacGroupFormComponent } from '../../components/rbac/group-form/rbac-group-form.component';
import { ADD_SERVICE_PROVIDER } from '../../shared/add-component/add-service-model';
import { AddButtonComponent } from '../../shared/add-component';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { RbacEntityListDirective } from '@app/abstract-directives/rbac-entity-list.directive';
import { RbacGroupService } from '../../services/rbac-group.service';

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

  component = RbacGroupFormComponent;

  @ViewChild(AddButtonComponent) addButton: AddButtonComponent;

  listColumns = [
    {
      type: 'choice',
      modelKey: 'checked',
      className: 'choice-column',
      headerClassName: 'choice-column',
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
      value: userNameMapper,
    }
  ] as IColumns<RbacGroupModel>;

  type: TypeName = 'rbac_group';

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

  clickRow(data: RowEventData): void {
    this.showForm(data);
  }

  showForm(data: RowEventData): void {
    this.addButton.showForm(this.entityService.model(data.row));
  }

}
