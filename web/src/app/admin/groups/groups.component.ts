import { Component, ViewChild } from '@angular/core';
import { IColumns, RowEventData } from '@adwp-ui/widgets';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { Store } from '@ngrx/store';
import { RbacGroupModel } from '@app/models/rbac/rbac-group.model';
import { TypeName } from '../../core/types';
import { RbacGroupComponent } from '../../components/rbac/group/rbac-group.component';
import { ADD_SERVICE_PROVIDER } from '../../shared/add-component/add-service-model';
import { RbacGroupService } from '../../components/rbac/group/rbac-group.service';
import { AddButtonComponent } from '../../shared/add-component';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { RbacEntityListDirective } from '@app/abstract-directives/rbac-entity-list.directive';

@Component({
  selector: 'app-groups',
  templateUrl: './groups.component.html',
  styleUrls: ['./groups.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: RbacGroupService }
  ],
})
export class GroupsComponent extends RbacEntityListDirective<RbacGroupModel> {

  component = RbacGroupComponent;

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
      value: (row) => row.user.map(i => i['id']).join(', '),
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

  clickRow(data: RowEventData) {
    this.showForm(data);
  }

  showForm(data: RowEventData): void {
    this.addButton.showForm({
      name: 'Edit group',
      component: this.component,
      value: data.row
    });
  }

}
