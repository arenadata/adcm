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
import { Issue } from '@app/core/types';

import { ComponentData } from './tooltip/tooltip.service';

export interface IIssueInfo {
  id: number;
  issue: Issue;
  cluster_id?: number;
  name?: string;
  path?: string;
}

@Component({
  selector: 'app-issue-info',
  template: `
    <div>{{ intro }}</div>
    <div *ngFor="let name of namesIssue">
      <ng-container *ngIf="isArray(current.issue[name]); else item_tpl">
        <div class="item-step">
          {{ name }}:
          <span *ngFor="let o of current.issue[name]">
            <b>{{ o.name }}</b> <app-issue-info [current]="o" [path]="name" [intro]="''" [parent]="current"></app-issue-info>
          </span>
        </div>
      </ng-container>
      <ng-template #item_tpl>
        <a [routerLink]="[Path, current.id, IssuePatch[name] || name]">{{ IssueNames[name] || name }}</a>
      </ng-template>
    </div>
  `,
  styles: ['a, .item-step { display: block; margin: 6px 0 8px 12px; white-space: nowrap;}'],
})
export class IssueInfoComponent implements OnInit {
  issues: Issue;
  @Input() intro = 'Issues in:';
  @Input() path: string;
  @Input() current: IIssueInfo;
  @Input() parent: IIssueInfo;

  IssuePatch = {
    required_service: 'service',
    required_import: 'import',
  };

  IssueNames = {
    config: 'Configuration',
    host_component: 'Host - Components',
    required_service: 'Required a service',
    required_import: 'Required a import',
  };

  constructor(private componentData: ComponentData) {}

  ngOnInit(): void {
    this.current = this.current || this.componentData.current;
    this.path = this.path || this.componentData.path;
    this.current.path = this.path;
    this.componentData.emitter.emit('Done');
  }

  get Path() {
    return this.parent && this.parent.cluster_id !== this.current.id ? `${this.parent.path}/${this.parent.id}/${this.path}` : this.path;
  }

  isArray(issue: [] | false): boolean {
    return Array.isArray(issue);
  }

  get namesIssue() {
    return Object.keys(this.current.issue || {});
  }
}
