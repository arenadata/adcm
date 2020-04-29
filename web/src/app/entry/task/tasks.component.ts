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
import { animate, state, style, transition, trigger } from '@angular/animations';
import { Component, ElementRef, OnInit, QueryList, ViewChild, ViewChildren } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { MatSort, MatSortHeader } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';
import { ApiService } from '@app/core/api';
import { EventMessage, SocketState } from '@app/core/store';
import { JobStatus, Task } from '@app/core/types';
import { DialogComponent, SocketListenerDirective } from '@app/shared';
import { Store } from '@ngrx/store';
import { filter, switchMap } from 'rxjs/operators';

export interface ICanDoActions {
  type: 'cluster' | 'host' | 'service' | 'provider';
  id: number;
  name: string;
}

@Component({
  selector: 'app-tasks',
  templateUrl: './task.component.html',
  styleUrls: ['./task.component.scss'],
  animations: [
    trigger('jobsExpand', [
      state('collapsed', style({ height: '0px', minHeight: '0' })),
      state('expanded', style({ height: '*' })),
      transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ],
})
export class TasksComponent extends SocketListenerDirective implements OnInit {
  isDisabled = false;

  dataSource = new MatTableDataSource<Task>([]);
  columnsToDisplay = ['id', 'name', 'objects', 'start_date', 'finish_date', 'status'];
  expandedTask: Task | null;

  paramMap: ParamMap;
  dataCount = 0;

  @ViewChild(MatPaginator, { static: true })
  paginator: MatPaginator;

  @ViewChild(MatSort, { static: true })
  sort: MatSort;

  @ViewChildren(MatSortHeader, { read: ElementRef }) matSortHeader: QueryList<ElementRef>;

  constructor(private api: ApiService, protected store: Store<SocketState>, public router: Router, public route: ActivatedRoute, public dialog: MatDialog) {
    super(store);
  }

  getIcon(status: string) {
    switch (status) {
      case 'aborted':
        return 'block';
      default:
        return 'done_all';
    }
  }

  ngOnInit() {
    const limit = +localStorage.getItem('limit');
    if (!limit) localStorage.setItem('limit', '10');
    this.paginator.pageSize = +localStorage.getItem('limit');

    this.route.paramMap.pipe(this.takeUntil()).subscribe((p) => {
      this.paramMap = p;
      if (+p.get('page') === 0) {
        this.paginator.firstPage();
      }
      const ordering = p.get('ordering');
      if (ordering && !this.sort.active) {
        this.sort.direction = ordering[0] === '-' ? 'desc' : 'asc';
        this.sort.active = ordering[0] === '-' ? ordering.substr(1) : ordering;
      }

      this.refresh();
    });

    super.startListenSocket();
  }

  cancelTask(url: string) {
    this.dialog
      .open(DialogComponent, {
        data: {
          text: 'Are you sure?',
          controls: ['Yes', 'No'],
        },
      })
      .beforeClosed()
      .pipe(
        filter((yes) => yes),
        switchMap(() => this.api.put(url, {}))
      )
      .subscribe();
  }

  buildLink(items: ICanDoActions[]) {
    const c = items.find((a) => a.type === 'cluster');
    const url = (a: ICanDoActions) => (a.type === 'cluster' || !c ? ['/', a.type, a.id] : ['/cluster', c.id, a.type, a.id]);
    return items.map((a) => ({ url: url(a), name: a.name }));
  }

  socketListener(m: EventMessage) {
    if (m.object.type === 'task' && m.event === 'change_job_status' && m.object.details.type === 'status' && m.object.details.value === 'created') {
      this.addTask(m.object.id);
      return;
    }

    const row = this.dataSource.data.find((a) => a.id === m.object.id);
    if (m.event === 'change_job_status') {
      if (row && m.object.type === 'task') {
        row.finish_date = new Date().toISOString();
        row.status = m.object.details.value as JobStatus;
      }
      if (m.object.type === 'job') {
        const task = this.dataSource.data.find((a) => a.jobs.some((b) => b.id === m.object.id));
        if (task) {
          const job = task.jobs.find((a) => a.id === m.object.id);
          if (job) {
            job.status = m.object.details.value as JobStatus;
            if (m.object.details.type === 'status' && m.object.details.value === 'running') job.start_date = new Date().toISOString();
            if (m.object.details.type === 'status' && (m.object.details.value === 'success' || m.object.details.value === 'failed')) job.finish_date = new Date().toISOString();
          }
        }
      }
    }
  }

  addTask(id: number) {
    this.isDisabled = true;
    this.api.getOne<Task>('task', id).subscribe((task) => {
      this.paginator.length = ++this.dataCount;
      if (this.paginator.pageSize > this.dataSource.data.length) this.dataSource.data = [task, ...this.dataSource.data];
      else {
        const [last, ...ost] = this.dataSource.data.reverse();
        this.dataSource.data = [task, ...ost.reverse()];
      }
      this.dataSource._updateChangeSubscription();
      setTimeout((_) => (this.isDisabled = false), 500);
    });
  }

  refresh() {
    this.api.root.pipe(switchMap((root) => this.api.getList<Task>(root.task, this.paramMap))).subscribe((data) => {
      this.dataSource.data = data.results;
      this.paginator.length = data.count;
      this.dataCount = data.count;
      if (data.results.length) localStorage.setItem('lastJob', data.results[0].id.toString());
      this.dataSource._updateChangeSubscription();
    });
  }

  pageHandler(pageEvent: PageEvent) {
    localStorage.setItem('limit', String(pageEvent.pageSize));
    const f = this.route.snapshot.paramMap.get('filter') || '';
    const ordering = null; // this.getSortParam(this.sort);
    this.router.navigate(['./', { page: pageEvent.pageIndex, limit: pageEvent.pageSize, filter: f, ordering }], {
      relativeTo: this.route,
    });
  }

  trackBy(item: any) {
    return item.id || item;
  }
}
