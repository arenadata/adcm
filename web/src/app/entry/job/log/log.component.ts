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
import { ClusterService } from '@app/core';
import { EventMessage, SocketState } from '@app/core/store';
import { Job, JobStatus, LogFile } from '@app/core/types';
import { SocketListenerDirective } from '@app/shared';
import { Store } from '@ngrx/store';
import { Subject } from 'rxjs';

import { TextComponent } from './text.component';

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
    <app-job-info [timeInfo]="timeInfo" [status]="job.status"></app-job-info>
    <div class="wrap" *ngIf="currentLog$ | async as log">
      <app-log-text *ngIf="log.type !== 'check'" [content]="log.content" [status]="job.status" (refresh)="refresh()"></app-log-text>
      <mat-accordion *ngIf="log.type === 'check'" class="accordion">
        <app-log-check [content]="log.content"></app-log-check>
      </mat-accordion>
    </div>
  `,
})
export class LogComponent extends SocketListenerDirective implements OnInit {
  currentLog$ = new Subject<LogFile>();
  timeInfo: ITimeInfo;
  logUrl: string;

  @ViewChild(TextComponent, { static: true }) textComp: TextComponent;

  constructor(private service: ClusterService, private route: ActivatedRoute, public store: Store<SocketState>) {
    super(store);
  }

  get job(): Job {
    return this.service.Current as Job;
  }

  ngOnInit() {
    this.timeInfo = this.service.getOperationTimeData(this.job);
    this.route.paramMap.pipe(this.takeUntil()).subscribe((p) => {
      this.logUrl = this.job.log_files.find((a) => a.id === +p.get('log')).url;
      this.refresh();
    });
    this.startListenSocket();
  }

  socketListener(m: EventMessage) {
    if (m?.object?.type === 'job' && m?.object?.id === this.job.id) {
      if (m.event === 'change_job_status') {
        const job = this.job;
        job.status = m.object.details.value as JobStatus;
        job.finish_date = new Date().toISOString();
        this.timeInfo = this.service.getOperationTimeData(job);
        if (this.textComp) this.textComp.update(job.status);
      }
      this.refresh();
    }
  }

  refresh() {
    if (!this.logUrl) return;
    this.service.getLog(this.logUrl).subscribe((a) => this.currentLog$.next(a));
  }
}
