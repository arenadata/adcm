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
import { Component } from '@angular/core';
import { IColumns } from '@app/adwp';

import { TypeName } from '@app/core/types';
import { ListFactory } from '@app/factories/list.factory';
import { ConcernListDirective } from '@app/abstract-directives/concern-list.directive';
import { ConcernEventType } from '@app/models/concern/concern-reason';

@Component({
  selector: 'app-hostprovider',
  template: `
    <mat-toolbar class="toolbar">
      <app-crumbs [navigation]="[{ url: '/provider', title: 'providers' }]"></app-crumbs>
      <app-add-button [name]="type" (added)="current = $event">Create {{ type }}</app-add-button>
    </mat-toolbar>

    <adwp-list
      [columns]="listColumns"
      [dataSource]="data$ | async"
      [paging]="paging | async"
      [sort]="sorting | async"
      [defaultSort]="defaultSort"
      [currentId]="current ? current.id : undefined"
      (clickRow)="clickRow($event)"
      (auxclickRow)="auxclickRow($event)"
      (changePaging)="onChangePaging($event)"
      (changeSort)="onChangeSort($event)"
    ></adwp-list>
  `,
  styles: [':host { flex: 1; }'],
})
export class HostproviderComponent extends ConcernListDirective<any> {

  type: TypeName = 'provider';
  eventTypes = [ConcernEventType.HostProvider];

  listColumns = [
    ListFactory.nameColumn(),
    ListFactory.bundleColumn(),
    ListFactory.stateColumn(),
    ListFactory.actionsButton(this),
    ListFactory.updateColumn(),
    ListFactory.configColumn(this),
    ListFactory.deleteColumn(this),
  ] as IColumns<any>;

}
