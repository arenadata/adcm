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
import { Cluster, IAction, Issue, notIssue } from '@app/core/types';
import { UpgradeItem } from '@app/shared/components';
import { Observable, of } from 'rxjs';

import { IDetails, INavItem } from '../details.service';
import { NavigationService } from '../navigation.service';

@Component({
  selector: 'app-details-top',
  template: `
    <app-crumbs [navigation]="items"></app-crumbs>
    <div class="example-spacer"></div>
    <app-upgrade *ngIf="upgradable" [dataRow]="upgrade"></app-upgrade>
    <app-actions [source]="actions" [isIssue]="eIssue" [cluster]="cluster"></app-actions>
  `,
  styles: [':host {display: flex;width: 100%;}']
})
export class TopComponent {
  items: INavItem[];
  cluster: { id: number; hostcomponent: string };
  eIssue: boolean;
  upgrade: UpgradeItem;

  @Input() set isIssue(v: boolean) {
    this.eIssue = v;
    if (this.upgrade) this.upgrade.issue = (v ? { issue: '' } : {}) as Issue;
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
      const { id, hostcomponent, issue, upgradable, upgrade } = c.parent || (c as Partial<Cluster>);
      this.cluster = { id, hostcomponent };
      this.upgradable = upgradable;
      this.eIssue = !notIssue(issue);
      this.upgrade = { issue, upgradable, upgrade };
    }
  }
  constructor(private navigation: NavigationService) {}
}
