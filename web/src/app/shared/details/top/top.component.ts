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
import { IAction } from '@app/core/types';
import { Observable, of } from 'rxjs';

import { IDetails, INavItem } from '../details.service';
import { NavigationService } from '../navigation.service';

@Component({
  selector: 'app-details-top',
  template: `
    <app-crumbs [navigation]="items"></app-crumbs>
    <div class="example-spacer"></div>
    <app-upgrade *ngIf="upgradable && !isIssue" [dataRow]="current"></app-upgrade>
    <app-actions [source]="actions$" [isIssue]="isIssue" [cluster]="cluster"></app-actions>
  `,
  styles: [':host {display: flex;width: 100%;}']
})
export class TopComponent {
  actions$: Observable<IAction[]> = of([]);
  items: INavItem[];
  cluster: { id: number; hostcomponent: string };
  isIssue: boolean;
  upgradable: boolean;

  @Input() set current(c: IDetails) {
    if (c) {
      this.items = this.navigation.getCrumbs(c);     
      this.actions$ = !c.actions || !c.actions.length ? of([]) : of(c.actions);
      this.isIssue = c.issue && !!Object.keys(c.issue).length;
      this.upgradable = c.upgradable;
      const { id, hostcomponent } = { ...(c.parent || c) };
      this.cluster = { id, hostcomponent };
    }
  }
  constructor(private navigation: NavigationService) {}
}
