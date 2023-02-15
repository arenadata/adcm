import { Component, ElementRef, Input, ViewChild } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

import { NotificationsData } from '@app/components/bell/bell.component';
import { TaskRaw } from '@app/core/types';
import { PopoverEventFunc } from '@app/abstract-directives/popover-content.directive';

export const ACKNOWLEDGE_EVENT = 'acknowledge';

@Component({
  selector: 'app-notifications',
  template: `
    <div class="counters">
      <div class="item" routerLink="/task" [queryParams]="{ status: 'running' }" matTooltip="Show jobs in progress">
        <mat-icon class="running">autorenew</mat-icon> {{ (data?.counts | async)?.runningCount }}
      </div>
      <div class="item" routerLink="/task" [queryParams]="{ status: 'success' }" matTooltip="Show success jobs">
        <mat-icon class="success">done_all</mat-icon> {{ (data?.counts | async)?.successCount }}
      </div>
      <div class="item" routerLink="/task" [queryParams]="{ status: 'failed' }" matTooltip="Show failed jobs">
        <mat-icon class="failed">done_all</mat-icon> {{ (data?.counts | async)?.failedCount }}
      </div>
    </div>

    <ng-container *ngIf="(data?.tasks | async)?.length; else empty">
      <div class="header">
        <span>Last {{(data.tasks | async)?.length}} notifications:</span>
      </div>

      <div class="notifications" #notifications>
        <div *ngFor="let task of (data.tasks | async)" class="notification">
          <ng-container [ngSwitch]="task.status">
            <mat-icon *ngSwitchCase="'running'" class="icon-locked running">autorenew</mat-icon>
            <mat-icon *ngSwitchCase="'aborted'" [ngClass]="task.status">block</mat-icon>
            <mat-icon *ngSwitchDefault [ngClass]="task.status">done_all</mat-icon>
          </ng-container>
          <a [routerLink]="['job', jobId(task), 'main']">{{ task?.action?.display_name }}</a>
        </div>

        <div class="footer">
          <a routerLink="/task">Show more...</a>
          <a (click)="acknowledge()" class="acknowledge"><mat-icon class="success">check_circle</mat-icon>acknowledge</a>
        </div>

      </div>
    </ng-container>
    <ng-template #empty>
      <div class="empty-label" [ngStyle]="{ 'min-height': minHeightNotifications + 'px' }">
        Nothing to display
      </div>
      <div class="empty-footer">
        <a routerLink="/task">Show all jobs...</a>
      </div>
    </ng-template>
  `,
  styleUrls: ['./notifications.component.scss']
})
export class NotificationsComponent {

  minHeightNotifications = 200;

  @ViewChild('notifications', { static: false }) notificationsRef: ElementRef;

  @Input() data: { counts: BehaviorSubject<NotificationsData>, tasks: BehaviorSubject<TaskRaw[]> };

  event: PopoverEventFunc;

  jobId(task) {
    const endStatuses = ['aborted', 'success', 'failed'];

    if (task.status === 'running') {
      const runningJob = task.jobs.find(job => job.status === 'running');

      if (runningJob) {
        return runningJob.id;
      }

      const createdJob = task.jobs.find(job => job.status === 'created');

      if (createdJob) {
        return createdJob.id;
      }

      const descOrderedJobs = task.jobs.slice().reverse();
      const finishedJob = descOrderedJobs.find(job => endStatuses.includes(job.status));

      if (finishedJob) {
        return finishedJob.id;
      }
    } else if (endStatuses.includes(task.status)) {
      const descOrderedJobs = task.jobs.slice().reverse();
      const finishedJob = descOrderedJobs.find(job => endStatuses.includes(job.status));

      if (finishedJob) {
        return finishedJob.id;
      }
    }
  }

  setLabelHeightAfterAcknowledge() {
    this.minHeightNotifications = this.notificationsRef.nativeElement.clientHeight;
  }

  acknowledge() {
    this.setLabelHeightAfterAcknowledge();
    this.event(ACKNOWLEDGE_EVENT);
  }

}
