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
import { Component, OnInit, ComponentRef } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { filter } from 'rxjs/operators';
import { BehaviorSubject } from 'rxjs';
import { BaseDirective, IColumns, IListResult, InstanceTakenFunc, Paging } from '@adwp-ui/widgets';
import { DateHelper } from '@app/helpers/date-helper';

import { EventMessage } from '@app/core/store';
import { JobStatus, Task, Job } from '@app/core/types';
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
})
export class TasksComponent extends BaseDirective implements OnInit {

  JobsComponent = JobsComponent;
  expandedTask = new BehaviorSubject<Task | null>(null);

  data$: BehaviorSubject<IListResult<Task>> = new BehaviorSubject(null);
  paging: BehaviorSubject<Paging> = new BehaviorSubject<Paging>(null);

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

  constructor(
    public route: ActivatedRoute,
    private taskService: TaskService,
    private jobService: JobService,
  ) {
    super();
  }

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
    this.taskService.events(['change_job_status'])
      .pipe(this.takeUntil())
      .subscribe(event => this.taskChanged(event));

    this.jobService.events(['change_job_status'])
      .pipe(this.takeUntil())
      .subscribe(event => this.jobChanged(event));
  }

  initPaging() {
    this.paging.pipe(
      this.takeUntil(),
      filter(paging => !!paging),
    ).subscribe((paging) => {
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
      this.paging.next({ pageIndex: page, pageSize: limit });
    });
  }

  ngOnInit() {
    this.initPaging();

    const limit = +localStorage.getItem('limit');
    if (!limit) localStorage.setItem('limit', '10');

    this.startListen();
  }

}
