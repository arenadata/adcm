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
import { Component, Input } from '@angular/core';
import { ApiBase, Issue } from '@app/core/types';

import { NavigationService, INavItem } from '../navigation.service';

@Component({
  selector: 'app-details-left',
  template: `
    <mat-nav-list>
      <a mat-list-item [appForTest]="'tab_' + item.url" *ngFor="let item of items" [routerLink]="[item.url]" routerLinkActive="active">
        <span>{{ item.title }}</span>
        &nbsp;
        <button *ngIf="item.action" mat-icon-button color="primary" (click)="btnClick(item.action)"><mat-icon>cloud_download</mat-icon></button>
        <mat-icon *ngIf="item.issue" color="warn">priority_hight</mat-icon>
        <mat-icon *ngIf="item.url === 'status'" [color]="item.status === 0 ? 'accent' : 'warn'">{{ item.status === 0 ? 'check_circle_outline' : 'error_outline' }}</mat-icon>
      </a>
    </mat-nav-list>
  `,
  styles: ['mat-nav-list {padding-top: 20px;}', 'a span { white-space: nowrap; }'],
})
export class LeftComponent {
  items: INavItem[] = [];
  @Input() set current(c: Partial<ApiBase>) {
    if (c) this.items = this.navigation.getLeft(c);
  }

  @Input() set issues(i: Issue) {
    this.items = this.items.map((a) => ({ ...a, issue: this.navigation.findIssue(a.url, i || {}) ? 'issue' : '' }));
  }

  @Input() set status(v: number) {
    const b = this.items.find((a) => a.url === 'status');
    if (b) b.status = v;
  }

  constructor(private navigation: NavigationService) {}

  btnClick(action: () => void) {
    action();
  }
}
