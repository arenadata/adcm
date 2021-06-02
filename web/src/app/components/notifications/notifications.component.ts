import { Component, Input, OnInit } from '@angular/core';

import { NotificationsData } from '@app/components/bell/bell.component';
import { BehaviorSubject } from 'rxjs';
import { TaskRaw } from '@app/core/types';

@Component({
  selector: 'app-notifications',
  template: `
    <div class="counters">
      <div class="item" routerLink="/task" [queryParams]="{ status: 'running' }">
        <mat-icon class="running">autorenew</mat-icon> {{ (data.counts | async).runningCount }}
      </div>
      <div class="item" routerLink="/task" [queryParams]="{ status: 'success' }">
        <mat-icon class="success">done_all</mat-icon> {{ (data.counts | async).successCount }}
      </div>
      <div class="item" routerLink="/task" [queryParams]="{ status: 'failed' }">
        <mat-icon class="failed">done_all</mat-icon> {{ (data.counts | async).failedCount }}
      </div>
    </div>

    <div *ngIf="(data.tasks | async)?.length" class="notifications">
      <div *ngFor="let task of (data.tasks | async)" class="notification">
        <ng-container [ngSwitch]="task.status">
          <mat-icon *ngSwitchCase="'running'" class="icon-locked running">autorenew</mat-icon>
          <mat-icon *ngSwitchCase="'aborted'" [ngClass]="task.status">block</mat-icon>
          <mat-icon *ngSwitchDefault [ngClass]="task.status">done_all</mat-icon>
        </ng-container>
        <a [routerLink]="['job', task.id]">{{ task.action.display_name }}</a>
        <mat-icon *ngIf="task.terminatable" class="failed">cancel</mat-icon>
      </div>
    </div>
  `,
  styleUrls: ['./notifications.component.scss']
})
export class NotificationsComponent implements OnInit {

  @Input() data: { counts: BehaviorSubject<NotificationsData>, tasks: BehaviorSubject<TaskRaw[]> };

  ngOnInit() {
    // this.data.tasks.subscribe(data => console.log('Tasks', data));
  }

}
