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
import { INavItem } from '../../../models/details';

@Component({
  selector: 'app-crumbs',
  template: `
    <mat-nav-list>
      <a routerLink="/admin"><mat-icon>apps</mat-icon></a>
      <span>&nbsp;{{ this.rootBreadcrumb() }}&nbsp;</span>
      <app-actions-button *ngIf="this.isAdminPage()"
                          class="crumbs-action-button"
                          [row]="{id: 1, hostcomponent: null, action: this.actionsUrl}">

      </app-actions-button>
      <ng-container *ngFor="let item of navigation; last as isLast; trackBy: trackBy">
        <a routerLink="{{ item.url }}">{{ item.title | uppercase }}</a>
        <mat-icon *ngIf="item.issue" [matTooltip]="item.issue" color="warn">priority_hight</mat-icon>
        <span *ngIf="!isLast">&nbsp;/&nbsp;</span>
      </ng-container>
    </mat-nav-list>
  `,
  styleUrls: ['./crumbs.component.scss'],
})
export class CrumbsComponent {
  @Input() navigation: INavItem[];
  @Input() actionsUrl: string;

  isAdminPage(): boolean {
    return this.navigation.length == 1 && this.navigation[0]?.path?.includes('admin');
  }

  rootBreadcrumb(): string {
    return this.isAdminPage() ? '/ ADCM' : '/';
  }

  trackBy(index: number, item: INavItem): string {
    return item.url;
  }
}
