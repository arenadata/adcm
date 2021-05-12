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
import { Component, ElementRef, OnInit, QueryList, ViewChild, ViewChildren, ComponentRef } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { MatSort, MatSortHeader } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { filter, switchMap } from 'rxjs/operators';
import { BehaviorSubject } from 'rxjs';
import { IColumns, IListResult, InstanceTakenFunc, Paging } from '@adwp-ui/widgets';
import { DateHelper } from '@app/helpers/date-helper';
import { Sort } from '@angular/material/sort';

import { ApiService } from '@app/core/api';
import { EventMessage, SocketState } from '@app/core/store';
import { JobStatus, Task, JobObject, Job } from '@app/core/types';
import { SocketListenerDirective } from '@app/shared/directives';
import { DialogComponent } from '@app/shared/components';
import { TaskObjectsComponent } from '@app/components/columns/task-objects/task-objects.component';
import { TaskStatusColumnComponent } from '@app/components/columns/task-status-column/task-status-column.component';
import { JobsComponent } from '@app/components/task/jobs/jobs.component';
import { TaskNameComponent } from '@app/components/columns/task-name/task-name.component';
import { TaskService } from '@app/services/task.service';
import { JobService } from '@app/services/job.service';

@Component({
  selector: 'app-tasks',
  templateUrl: './tasks.component.html',
  styleUrls: ['./tasks.component.scss'],
  animations: [
    trigger('jobsExpand', [
      state('collapsed', style({ height: '0px', minHeight: '0' })),
      state('expanded', style({ height: '*' })),
      transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ],
})
export class TasksComponent extends SocketListenerDirective implements OnInit {

  /* BEGIN: My editions */
  JobsComponent = JobsComponent;
  expandedTask = new BehaviorSubject<Task | null>(null);

  listColumns = [
    {
      label: '#',
      value: (row) => row.id,
      className: 'first-child',
      headerClassName: 'first-child',
    },
    {
      type: 'component',
      label: 'Action name',
      component: TaskNameComponent,
      instanceTaken: (componentRef: ComponentRef<TaskNameComponent>) => {
        componentRef.instance.expandedTask = this.expandedTask;
        componentRef.instance.toggleExpand = (row) => {
          this.expandedTask.next(
            this.expandedTask.value && this.expandedTask.value.id === row.id ? null : row
          );
        };
      },
    },
    {
      type: 'component',
      label: 'Objects',
      component: TaskObjectsComponent,
    },
    {
      label: 'Start date',
      value: row => DateHelper.short(row.start_date),
      className: 'action_date',
      headerClassName: 'action_date',
    },
    {
      label: 'Finish date',
      value: row => row.status === 'success' || row.status === 'failed' ? DateHelper.short(row.finish_date) : '',
      className: 'action_date',
      headerClassName: 'action_date',
    },
    {
      type: 'component',
      label: 'Status',
      component: TaskStatusColumnComponent,
      className: 'table-end center status',
      headerClassName: 'table-end center status',
    }
  ] as IColumns<Task>;

  jobsTableInstanceTaken: InstanceTakenFunc<Task> = (componentRef: ComponentRef<JobsComponent<Task>>) => {
    componentRef.instance.expandedTask = this.expandedTask;
  }

  data$: BehaviorSubject<IListResult<Task>> = new BehaviorSubject(null);
  nPaging: BehaviorSubject<Paging> = new BehaviorSubject<Paging>(null);
  nSort: BehaviorSubject<Sort> = new BehaviorSubject<Sort>(null);

  taskChanged(event: EventMessage): void {
    const data: IListResult<Task> = Object.assign({}, this.data$.value);
    if (event.object.details.type === 'status' && event.object.details.value === 'created') {
      if (this.data$.value.results.some((task) => task.id === event.object.id)) return;
      this.taskService.get(event.object.id).subscribe((task) => {
        data.results = [task, ...data.results];
        this.data$.next(data);
      });
    } else {
      const index = data.results.findIndex((a) => a.id === event.object.id);
      if (index > -1) {
        const task: Task = Object.assign({}, data.results[index]);
        task.finish_date = new Date().toISOString();
        task.status = event.object.details.value as JobStatus;
        data.results.splice(index, 1, task);
        this.data$.next(data);
      }
    }
  }

  jobChanged(event: EventMessage): void {
    const data: IListResult<Task> = Object.assign({}, this.data$.value);
    const taskIndex = data.results.findIndex(
      (item) => item.jobs.some((job) => job.id === event.object.id)
    );
    if (taskIndex > -1) {
      const task: Task = Object.assign({}, data.results[taskIndex]);
      const jobIndex = task.jobs.findIndex((item) => item.id === event.object.id);
      if (jobIndex > -1) {
        const job: Job = Object.assign({}, task.jobs[jobIndex]);
        job.status = event.object.details.value as JobStatus;
        if (event.object.details.type === 'status' && event.object.details.value === 'running') {
          job.start_date = new Date().toISOString();
        }
        if (
          event.object.details.type === 'status'
          && (event.object.details.value === 'success' || event.object.details.value === 'failed')
        ) {
          job.finish_date = new Date().toISOString();
        }
        task.jobs.splice(jobIndex, 1, job);
        data.results.splice(taskIndex, 1, task);
        this.data$.next(data);
      }
    }
  }

  startListen() {
    this.taskService.events(['change_job_status']).subscribe(event => this.taskChanged(event));
    this.jobService.events(['change_job_status']).subscribe(event => this.jobChanged(event));
  }

  initPaging() {
    this.nPaging.pipe(filter(paging => !!paging)).subscribe((paging) => {
      const params = {
        limit: paging.pageSize.toString(),
        offset: ((paging.pageIndex - 1) * paging.pageSize).toString(),
      };
      this.taskService.list(params).subscribe((resp) => {
        this.data$.next(resp);
      });
    });

    let limit = +localStorage.getItem('limit');
    if (!limit) localStorage.setItem('limit', '10');

    this.route.paramMap.pipe(this.takeUntil()).subscribe((p) => {
      const page = +p.get('page') ? +p.get('page') + 1 : 1;
      limit = p.get('limit') ? +p.get('limit') : +localStorage.getItem('limit');
      this.nPaging.next({ pageIndex: page, pageSize: limit });
    });
  }
  /* END: My editions */

  isDisabled = false;

  dataSource = new MatTableDataSource<Task>([]);
  columnsToDisplay = ['id', 'name', 'objects', 'start_date', 'finish_date', 'status'];

  paramMap: ParamMap;
  dataCount = 0;

  @ViewChild(MatPaginator, { static: true })
  paginator: MatPaginator;

  @ViewChild(MatSort, { static: true })
  sort: MatSort;

  @ViewChildren(MatSortHeader, { read: ElementRef }) matSortHeader: QueryList<ElementRef>;

  constructor(
    private api: ApiService,
    protected store: Store<SocketState>,
    public router: Router,
    public route: ActivatedRoute,
    public dialog: MatDialog,
    private taskService: TaskService,
    private jobService: JobService,
  ) {
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
    this.initPaging();
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
    this.startListen();
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
      if (this.dataSource.data.some((a) => a.id === id)) return;
      this.paginator.length = ++this.dataCount;
      task.objects = this.buildLink(task.objects);
      if (this.paginator.pageSize > this.dataSource.data.length) this.dataSource.data = [task, ...this.dataSource.data];
      else {
        const [last, ...ost] = this.dataSource.data.reverse();
        this.dataSource.data = [task, ...ost.reverse()];
      }
      this.dataSource._updateChangeSubscription();
      setTimeout((_) => (this.isDisabled = false), 500);
    });
  }

  buildLink(items: JobObject[]) {
    const c = items.find((a) => a.type === 'cluster');
    const url = (a: JobObject): string[] => (a.type === 'cluster' || !c ? ['/', a.type, `${a.id}`] : ['/', 'cluster', `${c.id}`, a.type, `${a.id}`]);
    return items.map((a) => ({ ...a, url: url(a) }));
  }

  refresh() {
    this.api.root.pipe(switchMap((root) => this.api.getList<Task>(root.task, this.paramMap))).subscribe((data) => {
      this.dataSource.data = data.results.map((a) => ({ ...a, objects: this.buildLink(a.objects) }));
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
