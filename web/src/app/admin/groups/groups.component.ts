import { Component, ViewChild } from '@angular/core';
import { IColumns, RowEventData } from '@adwp-ui/widgets';

import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { RbacGroupModel } from '@app/models/rbac/rbac-group.model';
import { TypeName } from '../../core/types';
import { RbacGroupComponent } from '../../components/rbac/group/rbac-group.component';
import { ADD_SERVICE_PROVIDER } from '../../shared/add-component/add-service-model';
import { RbacGroupService } from '../../components/rbac/group/rbac-group.service';
import { AddButtonComponent } from '../../shared/add-component';

@Component({
  selector: 'app-groups',
  templateUrl: './groups.component.html',
  styleUrls: ['./groups.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: RbacGroupService }
  ],
})
export class GroupsComponent extends AdwpListDirective<RbacGroupModel> {

  component = RbacGroupComponent;

  @ViewChild(AddButtonComponent) addButton: AddButtonComponent;

  listColumns = [
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
