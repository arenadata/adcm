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
import { Directive, Host, Input, OnDestroy, OnInit } from '@angular/core';
import { ParamMap } from '@angular/router';
import { EventMessage, SocketState } from '@app/core/store';
import { EmmitRow, Entities, getTypeName, Host as AdcmHost, TypeName, Bundle } from '@app/core/types';
import { Store } from '@ngrx/store';

import { SocketListener } from '../../directives/base.directive';
import { ListComponent } from '../list/list.component';
import { ListService } from './list.service';
import { filter } from 'rxjs/internal/operators/filter';
import { DialogComponent } from '../dialog.component';
import { switchMap } from 'rxjs/operators';

@Directive({
  selector: '[appBaseList]',
})
export class BaseListDirective extends SocketListener implements OnInit, OnDestroy {
  row: Entities;
  listParams: ParamMap;

  @Input('appBaseList') typeName: TypeName;
  constructor(@Host() private parent: ListComponent, private service: ListService, protected store: Store<SocketState>) {
    super(store);
  }

  ngOnInit(): void {
    this.parent.type = this.typeName;
    this.parent.columns = this.service.initInstance(this.typeName).columns;

    const limit = +localStorage.getItem('limit');
    if (!limit) localStorage.setItem('limit', '10');
    this.parent.paginator.pageSize = +localStorage.getItem('limit');

    this.parent.listItemEvt.pipe(this.takeUntil()).subscribe({ next: (event: EmmitRow) => this.listEvents(event) });

    this.parent.route.paramMap.pipe(this.takeUntil()).subscribe(p => {
      if (+p.get('page') === 0) {
        this.parent.paginator.firstPage();
      }
      const ordering = p.get('ordering');
      if (ordering && !this.parent.sort.active) {
        this.parent.sort.direction = ordering[0] === '-' ? 'desc' : 'asc';
        this.parent.sort.active = ordering[0] === '-' ? ordering.substr(1) : ordering;
        this.parent.sortParam = ordering;
      }

      this.listParams = p;
      this.refresh();
    });

    super.startListenSocket();
  }

  ngOnDestroy() {
    super.ngOnDestroy();
    this.parent.listItemEvt.complete();
  }

  socketListener(m: EventMessage): void {
    // if (this.typeName === 'job' && m.object.type === 'job' && m.event === 'change_job_status' && m.object.details.type === 'status') {
    //   if (m.object.details.value === 'created' || m.object.details.value === 'success') this.refresh();
    //   return;
    // }

    if (m.event === 'clear_issue' || m.event === 'raise_issue') return;

    const stype = `${m.object.type}${m.object.details.type ? '2' + m.object.details.type : ''}`;
    if (stype === this.typeName) {
      if (m.event === 'create' || m.event === 'delete' || m.event === 'add' || m.event === 'remove') {
        this.refresh(m.object.id);
        return;
      }
    }

    if (stype === 'host2provider' && m.event === 'create') {
      this.refresh(m.object.id);
      return;
    }

    // events for the row of list
    const row = this.parent.data.data.find(a => a.id === m.object.id);
    if (m.event === 'add' && stype === 'host2cluster' && row) {
      this.service.checkItem<AdcmHost>(row).subscribe(a => {
        const { cluster_id, cluster_name } = { ...a };
        row.cluster_id = cluster_id;
        row.cluster_name = cluster_name;
      });
    }

    if (getTypeName(this.typeName) === m.object.type) {
      if (row) {
        if (m.event === 'change_state') row.state = m.object.details.value;
        if (m.event === 'change_status') row.status = +m.object.details.value;
        if (m.event === 'change_job_status') row.status = m.object.details.value;
        if (m.event === 'upgrade') {
          this.service.checkItem(row).subscribe(item => Object.keys(row).map(a => (row[a] = item[a])));
        }
      } else console.warn('List :: object not found', m, this.parent.data.data, this.typeName);
    }
  }

  refresh(id?: number) {
    this.service.getList(this.listParams, this.typeName).subscribe(list => {
      this.parent.dataSource = list;
      if (id) this.parent.current = { id };
    });
  }

  listEvents(event: EmmitRow) {
    this.row = event.row;
    const { cmd, item } = event;
    this[cmd] && typeof this[cmd] === 'function' ? this[cmd](item) : console.warn(`No handler for ${cmd}`);
  }

  onLoad() {
    // loaded data
  }

  title() {
    this.parent.router.navigate(['./', this.row.id], { relativeTo: this.parent.route });
  }

  status() {
    this.parent.router.navigate(['./', this.row.id, 'status'], { relativeTo: this.parent.route });
  }

  config() {
    this.parent.router.navigate(['./', this.row.id, 'config'], { relativeTo: this.parent.route });
  }

  import() {
    this.parent.router.navigate(['./', this.row.id, 'import'], { relativeTo: this.parent.route });
  }

  license() {
    const row = this.row as Bundle;
    this.service.getLicenseInfo(row.license_url).subscribe(info =>
      this.parent.dialog
        .open(DialogComponent, {
          data: {
            title: `Accept license agreement`,
            text: info.text,
            controls: { label: 'Do you accept the license agreement?', buttons: ['Yes', 'No'] },
          },
        })
        .beforeClosed()
        .pipe(
          filter(yes => yes),
          switchMap(() => this.service.acceptLicense(`${row.license_url}accept/`)),
        )
        .subscribe(() => row.license = 'accepted'),
    );
  }

  getActions() {
    this.service.getActions(this.row);
  }

  delete() {
    this.service.delete(this.row).subscribe(() => (this.parent.current = null));
  }

  // host
  getClusters(arg) {
    if (!arg) this.service.getClustersForHost(this.row as any);
  }

  addCluster(id: number) {
    if (id) this.service.addClusterToHost(id, this.row as any);
  }
}
