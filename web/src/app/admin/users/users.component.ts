// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { Component, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { IColumns, RowEventData } from '@adwp-ui/widgets';
import { Store } from '@ngrx/store';
import { RbacUserModel } from '@app/models/rbac/rbac-user.model';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { TypeName } from '@app/core/types';
import { RbacEntityListDirective } from '@app/abstract-directives/rbac-entity-list.directive';
import { RbacUserComponent } from '../../components/rbac/user/rbac-user.component';
import { ADD_SERVICE_PROVIDER } from '../../shared/add-component/add-service-model';
import { AddButtonComponent } from '../../shared/add-component';
import { RbacUserService } from '../../services/rbac-user.service';

@Component({
  selector: 'app-users',
  templateUrl: './users.component.html',
  styleUrls: ['users.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: RbacUserService }
  ],
})
export class UsersComponent extends RbacEntityListDirective<RbacUserModel> implements OnInit {

  component = RbacUserComponent;

  @ViewChild(AddButtonComponent) addButton: AddButtonComponent;

  listColumns = [
    {
      type: 'choice',
      modelKey: 'checked',
      className: 'choice-column',
      headerClassName: 'choice-column',
    },
    {
      label: 'Username',
      sort: 'username',
      value: (row) => row.username,
    },
    {
      label: 'Email',
      sort: 'email',
      value: (row) => row.email,
    },
    {
      label: 'Groups',
      value: (row) => row.group.map((item) => item['id']).join(', '), //ToDo
    }
  ] as IColumns<RbacUserModel>;

  type: TypeName = 'rbac_user';

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected entityService: RbacUserService
  ) {
    super(service, store, route, router, dialog, entityService);
  }

  clickRow(data: RowEventData) {
    this.showForm(data);
  }

  showForm(data: RowEventData): void {
    this.addButton.showForm({
      name: 'Edit user',
      component: this.component,
      value: data.row
    });
  }

  getTitle(row: RbacUserModel): string {
    return row.username;
  }
}
