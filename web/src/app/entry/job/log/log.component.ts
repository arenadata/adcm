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
import { ActivatedRoute } from '@angular/router';
import { Subject } from 'rxjs';
import { filter, switchMap } from 'rxjs/operators';
import { BaseDirective } from '@app/adwp';

import { ClusterService } from '@app/core/services/cluster.service';
import { Job, JobStatus, LogFile } from '@app/core/types';
import { TextComponent } from './text.component';
import { JobService } from '@app/services/job.service';
import { EventMessage } from '@app/core/store';

export interface ITimeInfo {
  start: string;
  end: string;
  time: string;
}

@Component({
  selector: 'app-job-log',
  styles: [
    `
      :host {
        display: flex;
        flex: 1;
        padding: 10px 20px;
      }

      div.wrap {
        display: flex;
        flex: 1;
      }

      .accordion {
        flex: 1;
        display: flex;
        flex-direction: column;
      }
    `,
  ],
  template: `
    <ng-container *ngIf="job">
      <app-job-info [timeInfo]="timeInfo" [status]="job.status"></app-job-info>
      <div class="wrap" *ngIf="currentLog$ | async as log">
        <app-log-text *ngIf="log.type !== 'check'" [content]="log.content" [status]="job.status" (refresh)="refresh()"></app-log-text>
        <mat-accordion *ngIf="log.type === 'check'" class="accordion">
          <app-log-check [content]="log.content"></app-log-check>
        </mat-accordion>
      </div>
    </ng-container>
  `,
})
export class LogComponent extends BaseDirective implements OnInit {
  currentLog$ = new Subject<LogFile>();
  timeInfo: ITimeInfo;
  logUrl: string;

  job: Job;

  @ViewChild(TextComponent, { static: true }) textComp: TextComponent;

  constructor(
    private service: ClusterService,
    private route: ActivatedRoute,
    private jobService: JobService,
  ) {
    super();
  }

  socketListener(event: EventMessage) {
    if (event.event === 'change_job_status') {
      this.job.status = event.object.details.value as JobStatus;
      this.job.finish_date = new Date().toISOString();
      this.timeInfo = this.service.getOperationTimeData(this.job);
      if (this.textComp) this.textComp.update(this.job.status);
    }
    this.refresh();
  }

  startListenSocket() {
    this.jobService.events().pipe(
      this.takeUntil(),
      filter(event => event?.object?.id === this.job?.id),
    ).subscribe((event) => this.socketListener(event));
  }

  ngOnInit() {
    this.route.paramMap.pipe(
      this.takeUntil(),
      switchMap(() => this.jobService.get(+this.route.parent.snapshot.paramMap.get('job'))),
    ).subscribe((job) => {
      this.job = job;
      this.timeInfo = this.service.getOperationTimeData(this.job);
      this.logUrl = this.job.log_files.find((log) => log.id === +this.route.snapshot.paramMap.get('log'))?.url;
      this.refresh();
    });
    this.startListenSocket();
  }

  refresh() {
    if (!this.logUrl) return;
    this.service.getLog(this.logUrl).subscribe((a) => this.currentLog$.next(a));
  }

}
