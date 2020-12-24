// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apacoftware
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { Component, Input } from '@angular/core';
import { INavItem } from '../details/navigation.service';

@Component({
  selector: 'app-crumbs',
  template: `
    <mat-nav-list>
      <a routerLink="/admin"><mat-icon>apps</mat-icon></a>
      <span>&nbsp;/&nbsp;</span>
      <ng-container *ngFor="let item of navigation; last as isLast; trackBy: trackBy">
        <a routerLink="{{ item.url }}">{{ item.title | uppercase }}</a>
        <mat-icon *ngIf="item.issue" [matTooltip]="item.issue" color="warn">priority_hight</mat-icon>
        <span *ngIf="!isLast">&nbsp;/&nbsp;</span>
      </ng-container>
    </mat-nav-list>
  `,
  styles: [
    `
      :host {
        font-size: 0.8em;
        margin-left: 8px;
      }
      mat-nav-list {
        display: flex;
        align-items: center;
      }
      a {
        line-height: normal;
      }
      mat-icon {
        margin-bottom: 5px;
      }
    `,
  ],
})
export class CrumbsComponent {
  @Input() navigation: INavItem[];
  trackBy(index: number, item: INavItem) {
    return item.url;
  }
}
