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
import { IColumns } from '@adwp-ui/widgets';

import { TypeName } from '@app/core/types';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { ListFactory } from '@app/factories/list-factory';
import { UpgradeComponent } from '@app/shared';

@Component({
  selector: 'app-hostprovider',
  template: `
    <mat-toolbar class="toolbar">
      <app-crumbs [navigation]="[{ url: '/provider', title: 'providers' }]"></app-crumbs>
      <app-add-button [name]="type" (added)="list.current = $event">Create {{ type }}</app-add-button>
    </mat-toolbar>
    <app-list #list [type]="type"></app-list>

    <br>
    <br>

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
export class HostproviderComponent extends AdwpListDirective<any> {

  type: TypeName = 'provider';

  listColumns = [
    ListFactory.nameColumn(),
    ListFactory.bundleColumn(),
    ListFactory.stateColumn(),
    ListFactory.actionsColumn(),
    ListFactory.updateColumn(),
    ListFactory.configColumn(this),
    ListFactory.deleteColumn(this),
  ] as IColumns<any>;

}
