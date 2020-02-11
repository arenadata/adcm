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
import { ApiBase } from '@app/core/types';

import { ILeftMenuItem, NavigationService } from '../navigation.service';

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
export class LeftComponent implements OnInit {
  items: ILeftMenuItem[];
  @Input() set current(c) {
    if (c) this.items = this.navigation.getLeft(c);
  }

  constructor(private navigation: NavigationService) {}

  ngOnInit() {}
}
