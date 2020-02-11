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
import { Entities } from '@app/core/types';

@Component({
  selector: 'app-details-subtitle',
  template: `
    <ng-container *ngIf="current.typeName === 'job'; else link">
      <ng-container *ngFor="let o of current.objects; index as i; last as lastElement">
        <a [routerLink]="getParentLink(current.objects, i)">{{ o.name }}</a>
        <span *ngIf="!lastElement"> / </span>
      </ng-container>
    </ng-container>
    <ng-template #link>
      <a [routerLink]="['/', current.provider_id ? 'provider' : 'bundle', current.provider_id || current.bundle_id || {}]">
        {{ current.prototype_display_name || current.prototype_name }}
        {{ current.prototype_version }}
      </a>
    </ng-template>
  `,
  styles: []
})
export class SubtitleComponent {
  @Input() current: any = {};
  getParentLink(objects: { id: number; type: string }[], ind: number) {
    return objects.filter((a, i) => i <= ind).reduce((a, c) => [...a, c.type, c.id], ['/']);
  }
}
