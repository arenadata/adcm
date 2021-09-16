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
import { Component, OnInit } from '@angular/core';
import { IColumns } from '@adwp-ui/widgets';

import { ICluster } from '@app/models/cluster';
import { TypeName } from '@app/core/types';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { ListFactory } from '@app/factories/list-factory';
import { ListService } from '../../shared/components/list/list.service';
import { Store } from '@ngrx/store';
import { selectMessage, SocketState } from '../../core/store';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { ApiService } from '../../core/api';
import { ConcernService } from '../../services/concern.service';

@Component({
  template: `
    <mat-toolbar class="toolbar">
      <app-crumbs [navigation]="[{ url: '/cluster', title: 'clusters' }]"></app-crumbs>
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
  styles: [`
    :host {
      flex: 1;
      max-width: 100%;
    }
  `],
})
export class ClusterListComponent extends AdwpListDirective<ICluster> implements OnInit {

  type: TypeName = 'cluster';

  listColumns = [
    ListFactory.nameColumn(),
    ListFactory.bundleColumn(),
    ListFactory.descriptionColumn(),
    ListFactory.stateColumn(),
    ListFactory.statusColumn(this),
    ListFactory.actionsButton('cluster'),
    ListFactory.importColumn(this),
    ListFactory.updateColumn(),
    ListFactory.configColumn(this),
    ListFactory.deleteColumn(this),
  ] as IColumns<ICluster>;

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected api: ApiService,
    private concernService: ConcernService,
  ) {
    super(service, store, route, router, dialog, api);
  }

  ngOnInit() {
    super.ngOnInit();

    this.concernService.events().pipe(this.takeUntil()).subscribe(resp => console.log('Concern', resp));

    // return this.store.pipe(
    //   selectMessage,
    // ).subscribe(resp => console.log('Any', resp));
  }

}
