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
import { Component, DoCheck, ElementRef, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { interval, Subscription } from 'rxjs';
import { BaseDirective } from '@app/adwp';

import { JobStatus } from '@app/core/types/task-job';

@Component({
  selector: 'app-log-text',
  styles: [
    `
      :host {
        display: flex;
        flex: 1;
        flex-direction: column;
      }
      .tools {
        position: fixed;
        right: 60px;
        top: 150px;
      }
      textarea {
        background-color: #424242;
        border: 0;
        color: #fff;
        flex: 1;
      }
    `,
  ],
  template: `
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
    <textarea appScroll #tea (read)="read($event)" [readonly]="true">{{ content || 'Nothing to display...' }}</textarea>
  `,
})
export class TextComponent extends BaseDirective implements OnInit, DoCheck {
  isScroll = false;
  isRun = false;
  isWatch = false;
  watch: Subscription;
  @Input() content: string;
  @Input() status: JobStatus;
  @Output() refresh = new EventEmitter();

  @ViewChild('tea', { read: ElementRef }) textarea: ElementRef;

  ngOnInit(): void {
    this.isRun = this.status === 'running';
    if (this.isRun) this.startWatch();
  }

  ngDoCheck(): void {
    if (this.textarea) {
      const el = this.textarea.nativeElement;
      this.isScroll = el.offsetHeight < el.scrollHeight;
      if (this.isScroll && this.isWatch) this.down();
    }
  }

  update(status: JobStatus) {
    this.isRun = status === 'running';
    if (!this.isRun && this.isWatch) {
      this.isWatch = false;
      this.watch.unsubscribe();
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

  read(stop: { direct: -1 | 1 | 0 }) {
    if (this.isRun && this.isWatch && stop.direct === -1) {
      this.isWatch = false;
      this.watch.unsubscribe();
    }
    if (this.isRun && !this.isWatch && !stop.direct) this.startWatch();
  }

  startWatch() {
    this.isWatch = true;
    this.watch = interval(5000)
      .pipe(this.takeUntil())
      .subscribe(_ => this.refresh.emit());
  }
}
