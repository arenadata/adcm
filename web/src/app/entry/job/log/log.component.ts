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
import { AfterViewInit, Component, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ClusterService } from '@app/core';
import { EventMessage, SocketState } from '@app/core/store';
import { Job, JobStatus, LogFile } from '@app/core/types';
import { SocketListenerDirective } from '@app/shared';
import { Store } from '@ngrx/store';

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
    <app-job-info [timeInfo]="timeInfo" [status]="status"></app-job-info>
    <div class="wrap">
      <app-log-text *ngIf="!isCheck" [content]="currentLog.content" [status]="status" (refresh)="refresh()"></app-log-text>
      <mat-accordion *ngIf="isCheck" class="accordion">
        <app-log-check [content]="currentLog.content"></app-log-check>
      </mat-accordion>
    </div>
  `,
})
export class LogComponent extends SocketListenerDirective implements OnInit, AfterViewInit {
  currentLog = {} as LogFile;
  timeInfo: ITimeInfo;
  status: JobStatus;

  @ViewChild(TextComponent) textComp: TextComponent;

  constructor(private service: ClusterService, private route: ActivatedRoute, public store: Store<SocketState>) {
    super(store);
  }

  get job(): Job {
    return this.service.Current as Job;
  }

  get isCheck(): boolean {
    return this.currentLog.type === 'check';
  }

  ngOnInit() {
    this.status = this.job.status;
    this.timeInfo = this.service.getOperationTimeData(this.job);
    this.startListenSocket();
  }

  socketListener(m: EventMessage) {
    if (m && m.object && m.object.type === 'job' && m.object.id === this.job.id) {
      if (m.event === 'change_job_status') {
        this.status = m.object.details.value as JobStatus;
        if (this.textComp) this.textComp.update(m.object.details.value);

        const job = this.job;
        job.status = this.status;
        job.finish_date = new Date().toISOString();
        this.timeInfo = this.service.getOperationTimeData(job);
      }

      this.refresh();
    }
  }

  //
  ngAfterViewInit(): void {
    this.route.paramMap.pipe(this.takeUntil()).subscribe((p) => {
      this.currentLog.id = +p.get('log');
      this.refresh();
    });
  }

  refresh() {
    if (!this.currentLog.id) return;
    this.service
      .getLog(this.currentLog.id)
      .pipe(this.takeUntil())
      .subscribe((log) => (this.currentLog = log));
  }
}
