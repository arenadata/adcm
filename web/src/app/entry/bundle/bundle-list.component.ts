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
import { Component, ComponentRef, OnInit, ViewChild } from '@angular/core';
import { Store } from '@ngrx/store';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { IColumns } from '@app/adwp';
import { Observable } from 'rxjs';

import { StackService } from '../../core/services';
import { ClusterService } from '@app/core/services/cluster.service';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { TypeName } from '@app/core/types';
import { IBundle } from '@app/models/bundle';
import { ListFactory } from '../../factories/list.factory';
import { EditionColumnComponent } from '@app/components/columns/edition-column/edition-column.component';

@Component({
  selector: 'app-bundle-list',
  template: `
    <mat-toolbar class="toolbar">
      <app-crumbs [navigation]="[{ url: '/bundle', title: 'bundles' }]"></app-crumbs>
      <app-button-uploader #uploadBtn [color]="'accent'" [label]="'Upload bundles'"
                           (output)="upload($event)"></app-button-uploader>
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
export class BundleListComponent extends AdwpListDirective<IBundle> {

  type: TypeName = 'bundle';

  listColumns = [
    ListFactory.nameColumn(),
    {
      label: 'Version',
      sort: 'version',
      value: row => row.version,
    },
    {
      label: 'Edition',
      type: 'component',
      component: EditionColumnComponent,
      instanceTaken: (componentRef: ComponentRef<EditionColumnComponent>) => {
        componentRef.instance.onClick = this.license.bind(this);
      }
    },
    ListFactory.descriptionColumn(),
    ListFactory.deleteColumn(this),
  ] as IColumns<IBundle>;

  @ViewChild('uploadBtn', { static: true }) uploadBtn: any;

  constructor(
    private stack: StackService,
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
  ) {
    super(service, store, route, router, dialog);
  }

  upload(data: FormData[]) {
    this.stack.upload(data).subscribe();
  }

  license(data: { event: MouseEvent, action: string, row: any }) {
    this.clickCell(data.event, data.action, data.row);
  }

}

@Component({
  selector: 'app-main',
  template: `
    <adwp-table
      [columns]="listColumns"
      [dataSource]="model | pickKeys:keys | translateKeys | toDataSource"
    ></adwp-table>
  `,
  styles: [':host {width: 100%; max-width: 960px}']
})
export class MainComponent implements OnInit {
  model: any;

  keys = ['display_name', 'version', 'license', 'license_path'];

  listColumns = [
    ListFactory.keyColumn(),
    ListFactory.valueColumn(),
  ] as IColumns<any>;

  constructor(private service: ClusterService) {}

  ngOnInit() {
    this.model = this.service.Current;
  }

}

@Component({
  selector: 'app-license',
  template: `
    <pre>{{ text | async }}</pre>
  `,
  styles: [`:host {
    width: 100%;
    max-width: 960px
  }

  pre {
    white-space: pre-wrap;
  }`]
})
export class LicenseComponent implements OnInit {
  text: Observable<string>;

  constructor(private service: ClusterService) {}

  ngOnInit(): void {
    this.text = this.service.getBundleLicenseText();
  }

}
