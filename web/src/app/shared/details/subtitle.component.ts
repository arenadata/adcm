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
import { IDetails } from '@app/models/details';

@Component({
  selector: 'app-details-subtitle',
  template: `
    <ng-container *ngIf="cur">
      <ng-container *ngIf="cur.typeName === 'job'; else link">
        <app-task-objects [row]="cur"></app-task-objects>
      </ng-container>
      <ng-template #link>
        <a [routerLink]="['/', cur.provider_id ? 'provider' : 'bundle', cur.provider_id || cur.bundle_id || {}]">
          {{ cur.provider_name || '' }}
          {{ cur.typeName === 'host' ? '' : cur.prototype_display_name || cur.prototype_name }}
          {{ cur.typeName === 'host' ? '' : cur.prototype_version }}
        </a>
      </ng-template>
    </ng-container>
  `,
})
export class SubtitleComponent {
  cur: IDetails;

  @Input() set current(c: IDetails) {
    if (c) {
      this.cur = c;
    }
  }

}
