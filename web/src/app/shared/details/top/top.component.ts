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
    <app-upgrade *ngIf="upgradable && eIssue" [dataRow]="current"></app-upgrade>
    <app-actions [source]="actions" [isIssue]="eIssue" [cluster]="cluster"></app-actions>
  `,
  styles: [':host {display: flex;width: 100%;}']
})
export class TopComponent {
  items: INavItem[];
  cluster: { id: number; hostcomponent: string };
  eIssue: boolean;

  @Input() set isIssue(v: boolean) {
    this.eIssue = v;
    if (this.items) {
      const a = this.items.find(b => b.id);
      if (a) a.issue = this.navigation.getIssueMessage(v);
    }
  }

  @Input() upgradable: boolean;
  @Input() actions: Observable<IAction[]> = of([]);

  @Input() set current(c: IDetails) {
    if (c) {
      this.items = this.navigation.getCrumbs(c);
      const { id, hostcomponent } = { ...(c.parent || c) };
      this.cluster = { id, hostcomponent };
    }
  }
  constructor(private navigation: NavigationService) {}
}
