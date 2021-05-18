import { Component, Input, OnInit } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseDirective } from '@adwp-ui/widgets';

import { AdcmTypedEntity } from '@app/models/entity';
import { IAction } from '@app/core/types';
import { IIssues } from '@app/models/issue';
import { Store } from '@ngrx/store';
import { selectMessage } from '@app/core/store';

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
          <app-actions-button [row]="item?.entity" [issueType]="item?.entity?.typeName"></app-actions-button>
          <app-upgrade *ngIf="item?.entity?.typeName === 'cluster'" [row]="item?.entity"></app-upgrade>
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
      padding: 2px 0 2px 8px;
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
      line-height: normal;
      text-overflow: ellipsis;
      overflow: hidden;
      display: block;
    }

    .mat-nav-list app-upgrade {
      margin-left: -8px;
    }

  `],
})
export class NavigationComponent extends BaseDirective implements OnInit {

  actionFlag = false;
  actionLink: string;
  actions: IAction[] = [];
  state: string;
  disabled: boolean;
  cluster: { id: number; hostcomponent: string };

  private ownPath: Observable<AdcmTypedEntity[]>;

  isIssue = (issue: IIssues): boolean => !!(issue && Object.keys(issue).length);

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

  constructor(
    private store: Store,
  ) {
    super();
  }

  ngOnInit() {
    console.log('Ok');
    this.store.pipe(selectMessage).subscribe(event => console.log('Second', event));
  }

}
