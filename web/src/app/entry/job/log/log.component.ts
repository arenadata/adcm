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
import { AfterViewInit, Component, DoCheck, ElementRef, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ClusterService } from '@app/core';
import { EventMessage, SocketState } from '@app/core/store';
import { Job, JobStatus, LogFile } from '@app/core/types';
import { SocketListenerDirective } from '@app/shared';
import { Store } from '@ngrx/store';
import { interval, Subscription } from 'rxjs';

export interface ITimeInfo {
  start: string;
  end: string;
  time: string;
}

@Component({
  selector: 'app-job-log',
  templateUrl: './log.component.html',
  styleUrls: ['./log.component.scss']
})
export class LogComponent extends SocketListenerDirective implements OnInit, AfterViewInit, DoCheck {

  currentLog: Partial<LogFile> = {};

  timeInfo: ITimeInfo;
  status: JobStatus;

  isScroll = false;
  isRun = false;
  isWatch = false;
  watch: Subscription;

  @ViewChild('tea', { read: ElementRef }) textarea: ElementRef;

  constructor(private service: ClusterService, private route: ActivatedRoute, public store: Store<SocketState>) {
    super(store);
  }

  get job(): Job {
    return this.service.Current as Job;
  }

  ngOnInit() {
    this.status = this.job.status;
    this.timeInfo = this.service.getOperationTimeData(this.job);

    this.isRun = this.status === 'running';
    if (this.isRun) this.startWatch();

    this.startListenSocket();
  }

  socketListener(m: EventMessage) {
    if (m && m.object && m.object.type === 'job' && m.object.id === this.job.id) {
      this.isRun = m.object.details.value === 'running';
      if (!this.isRun && this.isWatch) {
        this.isWatch = false;
        this.watch.unsubscribe();
      }

      this.status = m.object.details.value as JobStatus;
      const job = this.job;
      job.status = this.status;
      job.finish_date = new Date().toISOString();
      this.timeInfo = this.service.getOperationTimeData(job);

      this.refresh();
    }
  }

  ngAfterViewInit(): void {
    this.route.paramMap.pipe(this.takeUntil()).subscribe(p => {
      this.currentLog.id = +p.get('log');
      this.refresh();
    });
  }

  ngDoCheck(): void {
    if (this.textarea) {
      const el = this.textarea.nativeElement;
      this.isScroll = el.offsetHeight < el.scrollHeight;
      if (this.isScroll && this.isWatch) this.down();
    }
  }

  down() {
    const el = this.textarea.nativeElement;
    el.scrollTop = el.scrollHeight;
    if (this.isRun && !this.isWatch) this.startWatch();
  }

  top() {
    const el = this.textarea.nativeElement;
    el.scrollTop = 0;
    if (this.isRun && this.isWatch) {
      this.isWatch = false;
      this.watch.unsubscribe();
    }
  }

  startWatch() {
    this.isWatch = true;
    this.watch = interval(5000)
      .pipe(this.takeUntil())
      .subscribe({ next: () => this.refresh() });
  }

  read(stop: { direct: -1 | 1 | 0 }) {
    if (this.isRun && this.isWatch && stop.direct === -1) {
      this.isWatch = false;
      this.watch.unsubscribe();
    }
    if (this.isRun && !this.isWatch && !stop.direct) this.startWatch();
  }

  refresh() {
    if (!this.currentLog.id) console.error('No `id` for current LogFile');
    this.service
      .getLog(this.currentLog.id)
      .pipe(this.takeUntil())
      .subscribe(log => (this.currentLog = log));
  }
}
