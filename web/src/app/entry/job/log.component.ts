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
import { ActivatedRoute, ParamMap } from '@angular/router';
import { ClusterService } from '@app/core';
import { EventMessage, SocketState } from '@app/core/store';
import { CheckLog, LogFile } from '@app/core/types';
import { SocketListenerDirective } from '@app/shared';
import { Store } from '@ngrx/store';
import { interval, Subscription } from 'rxjs';

import { JobInfoComponent } from './job-info.component';

@Component({
  selector: 'app-job-log',
  template: `
    <app-job-info #info></app-job-info>
    <div class="wrap" *ngIf="currentLog">
      <ng-container *ngIf="currentLog.format !== 'json'; else json">
        <div class="tools">
          <ng-container *ngIf="isScroll">
            <button color="accent" mat-icon-button (click)="down()" matTooltip="To the bottom" [disabled]="(isRun && isWatch) || !isScroll">
              <mat-icon>arrow_downward</mat-icon>
            </button>
            <button color="accent" mat-icon-button (click)="top()" matTooltip="To the top" [disabled]="!isScroll">
              <mat-icon>arrow_upward</mat-icon>
            </button>
          </ng-container>
        </div>
        <textarea class="log" appScroll #tea (read)="read($event)" [readonly]="true">{{ currentLog.body || 'Nothing to display...' }}</textarea>
      </ng-container>
      <ng-template #json>
        <mat-accordion class="accordion">
          <mat-expansion-panel *ngFor="let item of currentLog.body" class="panel">
            <mat-expansion-panel-header>
              <mat-panel-title>
                {{ item.title }}
              </mat-panel-title>
              <mat-panel-description class="item-info">
                <span [ngClass]="{ status: true, accent: item.result, warn: !item.result }">[ {{ item.result ? 'Success' : 'Fails' }} ]</span>
              </mat-panel-description>
            </mat-expansion-panel-header>
            <textarea class="check" [readonly]="true">{{ item.message }}</textarea>
          </mat-expansion-panel>
        </mat-accordion>
      </ng-template>
    </div>
  `,
  styles: [
    ':host {display: flex; flex: 1; flex-direction: column;}',
    '.tools { position: fixed; right: 60px; top: 150px; }',
    'div.wrap {display: flex; flex: 1; flex-direction: column;padding: 10px;}',
    'textarea.log, textarea.check {background-color: #424242; border: 0; color: #fff;flex: 1;}',
    'textarea.check {height: 300px;width: 100%;}',
    '.accordion {flex: 1; display: flex; flex-direction: column;}',
    '.status {white-space: nowrap;}',
    '.item-info {align-items: center; justify-content: flex-end;}'
  ]
})
export class LogComponent extends SocketListenerDirective implements OnInit, AfterViewInit, DoCheck {
  // content: CheckLog[] = [];
  currentLog: LogFile;

  isScroll = false;
  isRun = false;
  isWatch = false;
  watch: Subscription;

  @ViewChild('tea', { read: ElementRef }) textarea: ElementRef;
  @ViewChild('info', { static: true }) info: JobInfoComponent;

  constructor(private service: ClusterService, private route: ActivatedRoute, protected store: Store<SocketState>) {
    super(store);
  }

  ngOnInit() {
    this.isRun = this.service.Current.status.toString() === 'running';
    if (this.isRun) this.startWatch();
    this.startListenSocket();
  }

  socketListener(m: EventMessage) {
    if (m && m.object && m.object.type === 'job' && m.object.id === this.service.Current.id) {
      this.isRun = m.object.details.value === 'running';
      if (!this.isRun && this.isWatch) {
        this.isWatch = false;
        this.watch.unsubscribe();
      }
      this.refresh();
    }
  }

  ngAfterViewInit(): void {
    this.route.paramMap.pipe(this.takeUntil()).subscribe((p: ParamMap) => this.refresh(+p.get('log')));
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

  refresh(id?: number) {
    this.service
      .getLog(id || this.currentLog.id)
      .pipe(this.takeUntil())
      .subscribe(log => (this.currentLog = log));
  }
}
