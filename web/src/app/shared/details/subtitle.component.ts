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
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

import { IDetails } from './navigation.service';
import { JobObject } from '@app/core/types';
import { ObjectLinkColumnPipe } from '@app/shared/pipes/object-link-column/object-link-column.pipe';
import { SortObjectsPipe } from '@app/shared/pipes/sort-objects/sort-objects.pipe';

@Component({
  selector: 'app-details-subtitle',
  template: `
    <ng-container *ngIf="cur">
      <ng-container *ngIf="cur.typeName === 'job'; else link">
        <ng-container *ngFor="let obj of cur.objects; index as i; last as lastElement">
          <a [routerLink]="getUrl(obj, jobs(cur.objects))">{{ obj.name }}</a>
          <span *ngIf="!lastElement"> / </span>
        </ng-container>
      </ng-container>
      <ng-template #link>
        <a [routerLink]="['/', cur.provider_id ? 'provider' : 'bundle', cur.provider_id || cur.bundle_id || {}]">
          {{ cur.prototype_display_name || cur.prototype_name }}
          {{ cur.prototype_version }}
        </a>
      </ng-template>
    </ng-container>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SubtitleComponent {
  cur: IDetails;

  @Input() set current(c: IDetails) {
      if (c) {
      this.cur = c;
    }
  }

  getUrl(obj: JobObject, jobs: JobObject[]): string {
    return new ObjectLinkColumnPipe().transform(obj, jobs).url(null);
  }

  jobs(jobs: JobObject[]): JobObject[] {
    return new SortObjectsPipe().transform(jobs);
  }
}
