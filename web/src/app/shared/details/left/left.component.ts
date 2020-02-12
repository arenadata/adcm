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
import { Component, Input, OnInit } from '@angular/core';

import { INavItem, IDetails } from '../details.service';
import { NavigationService, Config, IssueSet } from '../navigation.service';
import { ApiBase, Job, Issue } from '@app/core/types';

@Component({
  selector: 'app-details-left',
  template: `
    <mat-nav-list>
      <a mat-list-item [appForTest]="'tab_' + item.url" *ngFor="let item of items" [routerLink]="[item.url]" routerLinkActive="active">
        <span>{{ item.title }}</span>
        &nbsp;
        <mat-icon *ngIf="item.issue" color="warn">priority_hight</mat-icon>
        <ng-container *ngIf="item.url === 'status'">
          <ng-container *ngTemplateOutlet="status; context: { status: item.status }"></ng-container>
        </ng-container>
      </a>
      <ng-template #status let-status="status">
        <mat-icon *ngIf="status === 0" color="accent">check_circle_outline</mat-icon>
        <mat-icon *ngIf="status !== 0" color="warn">error_outline</mat-icon>
      </ng-template>
    </mat-nav-list>
  `,
  styles: ['mat-nav-list {padding-top: 20px;}']
})
export class LeftComponent {
  items: INavItem[] = [];
  @Input() set current(c: ApiBase) {
    if (c) this.items = this.navigation.getLeft(c);
  }

  @Input() set issues(i: Issue) {
    if (!i) i = {} as Issue;
    this.items = this.items.map(a => ({ ...a, issue: this.navigation.setIssue(a.url, i) ? 'issue' : '' }));
  }

  @Input() set status(v: number) {
    const b = this.items.find(a => a.url === 'status');
    if (b) b.status = v;
  }

  constructor(private navigation: NavigationService) {}
}
