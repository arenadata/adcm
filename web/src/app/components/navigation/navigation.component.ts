import { Component, Input } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseDirective } from '@adwp-ui/widgets';

import { AdcmTypedEntity } from '@app/models/entity';
import { ISSUE_MESSAGE } from '@app/shared/details/navigation.service';
import { Cluster, IAction } from '@app/core/types';
import { IIssue } from '@app/models/issue';

@Component({
  selector: 'app-navigation',
  template: `
    <mat-nav-list>
      <a routerLink="/admin"><mat-icon>apps</mat-icon></a>
      <span>&nbsp;/&nbsp;</span>
      <ng-container *ngFor="let item of path | async | navItem; last as isLast">
        <span [ngClass]="item.class">
          <a routerLink="{{ item.url }}">{{ item.title | uppercase }}</a>
          <mat-icon
            *ngIf="isIssue(item.entity?.issue); else aggregate"
            [matTooltip]="ISSUE_MESSAGE"
            color="warn">
            priority_hight
          </mat-icon>
          <ng-template #aggregate><span class="aggregate"></span></ng-template>
        </span>
        <span *ngIf="!isLast">&nbsp;/&nbsp;</span>
      </ng-container>
    </mat-nav-list>

    <app-action-list
      *ngIf="actionFlag"
      [asButton]="true"
      [actionLink]="actionLink"
      [actions]="actions"
      [state]="state"
      [disabled]="disabled"
      [cluster]="cluster"
    ></app-action-list>
  `,
  styles: [`
    :host {
      font-size: 0.8em;
      margin-left: 8px;
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    mat-nav-list {
      padding-top: 0;
      display: flex;
      align-items: center;
    }

    mat-nav-list a {
      display: flex;
      align-items: center;
      line-height: normal;
    }

    .mat-nav-list .entity {
      border: 1px solid #54646E;
      border-radius: 5px;
      padding: 2px 0 2px 8px;
      display: flex;
      align-items: center;
      justify-content: space-around;
    }

    .mat-nav-list .entity a {
      line-height: 24px;
    }

    .aggregate {
      width: 7px;
    }

  `],
})
export class NavigationComponent extends BaseDirective {

  Object = Object;
  ISSUE_MESSAGE = ISSUE_MESSAGE;

  actionFlag = false;
  actionLink: string;
  actions: IAction[] = [];
  state: string;
  disabled: boolean;
  cluster: { id: number; hostcomponent: string };

  ownPath: Observable<AdcmTypedEntity[]>;
  isIssue = (issue: IIssue): boolean => !!(issue && Object.keys(issue).length);
  @Input() set path(path: Observable<AdcmTypedEntity[]>) {
    this.ownPath = path;
    this.ownPath.pipe(this.takeUntil()).subscribe((lPath) => {
      if (lPath) {
        const last = lPath[lPath.length - 1];
        const exclude = ['bundle', 'job'];
        this.actionFlag = !exclude.includes(last.typeName);
        this.actionLink = (<any>last).action;
        this.actions = (<any>last).actions;
        this.state = (<any>last).state;
        this.disabled = this.isIssue((<any>last).issue) || (<any>last).state === 'locked';
        const { id, hostcomponent } = <any>lPath[0];
        this.cluster = { id, hostcomponent };
      }
    });
  }
  get path(): Observable<AdcmTypedEntity[]> {
    return this.ownPath;
  }

}
