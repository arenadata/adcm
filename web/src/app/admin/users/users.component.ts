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
import { Component, OnInit, Type, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { IColumns } from '@adwp-ui/widgets';
import { Store } from '@ngrx/store';
import { RbacUserModel } from '@app/models/rbac/rbac-user.model';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { TypeName } from '@app/core/types';
import { RbacEntityListDirective } from '@app/abstract-directives/rbac-entity-list.directive';
import { ADD_SERVICE_PROVIDER } from '../../shared/add-component/add-service-model';
import { AddButtonComponent, BaseFormDirective } from '../../shared/add-component';
import { RbacUserService } from '../../services/rbac-user.service';
import { RbacUserFormComponent } from '../../components/rbac/user-form/rbac-user-form.component';
import { IFilter } from "../../shared/configuration/tools/filter/filter.component";
import { BehaviorSubject } from "rxjs";

const groupNameMapper = (user: RbacUserModel) => {
  return user.group.map((group) => group.name).join(', ');
};

@Component({
  selector: 'app-users',
  templateUrl: './users.component.html',
  styleUrls: ['users.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: RbacUserService }
  ],
})
export class UsersComponent extends RbacEntityListDirective<RbacUserModel> implements OnInit {
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
      className: 'one-line-string',
      value: groupNameMapper,
    },
    {
      label: 'Type',
      sort: 'type',
      value: (row) => row.type,
    }
  ] as IColumns<RbacUserModel>;

  type: TypeName = 'user'
  filteredData$: BehaviorSubject<any> = new BehaviorSubject<any>(null);

  userFilters: IFilter[] = [
    {
      id: 1, name: 'status', display_name: 'Status', filter_field: 'is_active', filter_type: 'list',
      options: [
        {id: 1, name: 'active', display_name: 'Active', value: true},
        {id: 2, name: 'inactive', display_name: 'Inactive', value: false},
      ]
    },
    {
      id: 2, name: 'type', display_name: 'Type', filter_field: 'type', filter_type: 'list',
      options: [
        {id: 1, name: 'local', display_name: 'Local', value: 'local'},
        {id: 2, name: 'ldap', display_name: 'Ldap', value: 'ldap'},
      ]
    }
  ]

  component: Type<BaseFormDirective> = RbacUserFormComponent;

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

  getTitle(row: RbacUserModel): string {
    return row.username;
  }

  isRowInactive = (value) => {
    return value?.is_active === false;
  }

}
