import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseDirective } from '@app/adwp';

import { AdcmTypedEntity } from '@app/models/entity';
import { EmmitRow, IAction } from '@app/core/types';
import { IIssues } from '@app/models/issue';

@Component({
  selector: 'app-navigation',
  template: `
    <mat-nav-list>
      <a routerLink="/admin"><mat-icon>apps</mat-icon></a>
      <span>&nbsp;/&nbsp;</span>
      <ng-container *ngFor="let item of path | async | navItem; last as isLast">
        <span [ngClass]="isLast ? [item.class, 'last'] : [item.class]">
          <div class="link">
            <a routerLink="{{ item.url }}" [title]="item.title | uppercase">{{ item.title | uppercase }}</a>
          </div>
          <app-actions-button *ngIf="item?.entity?.typeName !== 'group_config'"
                              [row]="item?.entity"></app-actions-button>
          <app-upgrade
            *ngIf="['cluster', 'provider'].includes(item?.entity?.typeName)"
            [row]="item?.entity"
            [type]="item?.entity?.typeName"
            (refresh)="refresh.emit($event)"
          ></app-upgrade>
        </span>
        <span *ngIf="!isLast">&nbsp;/&nbsp;</span>
      </ng-container>
    </mat-nav-list>
  `,
  styles: [`
    :host {
      font-size: 14px;
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
      max-width: 100%;
      overflow: hidden;
      flex-flow: row nowrap;
      justify-content: flex-start;
    }

    mat-nav-list > * {
      display: block;
      box-sizing: border-box;
    }

    mat-nav-list a {
      display: flex;
      align-items: center;
      line-height: normal;
    }

    .mat-nav-list .entity {
      border: 1px solid #54646E;
      border-radius: 5px;
      padding: 2px 8px;
      display: flex;
      align-items: center;
      justify-content: space-around;
      flex: 0 1 auto;
      overflow: hidden;

    }

    .mat-nav-list .entity.last {
      flex: 0 0 auto;
    }

    .mat-nav-list .entity * {
      flex: 0 0 auto;
    }

    .mat-nav-list .entity .link {
      flex: 0 1 auto;
      overflow: hidden;
    }

    .mat-nav-list .entity a {
      line-height: 40px;
      text-overflow: ellipsis;
      overflow: hidden;
      display: block;
    }

    .mat-nav-list app-upgrade {
      margin-left: -8px;
    }

  `],
})
export class NavigationComponent extends BaseDirective {

  actionFlag = false;
  actionLink: string;
  actions: IAction[] = [];
  state: string;
  cluster: { id: number; hostcomponent: string };

  private ownPath: Observable<AdcmTypedEntity[]>;

  isIssue = (issue: IIssues): boolean => !!(issue && Object.keys(issue).length);

  @Input() set path(path: Observable<AdcmTypedEntity[]>) {
    this.ownPath = path;
    this.ownPath.pipe(this.takeUntil()).subscribe((lPath) => {
      if (lPath && !!lPath.length) {
        const last = lPath[lPath.length - 1];
        const exclude = ['bundle', 'job'];
        this.actionFlag = !exclude.includes(last.typeName);
        this.actionLink = (<any>last).action;
        this.actions = (<any>last).actions;
        this.state = (<any>last).state;
        const { id, hostcomponent } = <any>lPath[0];
        this.cluster = { id, hostcomponent };
      }
    });
  }

  get path(): Observable<AdcmTypedEntity[]> {
    return this.ownPath;
  }

  @Output()
  refresh: EventEmitter<EmmitRow> = new EventEmitter<EmmitRow>();

}
