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
    <ng-container *ngIf="currentObject">
      <ng-container *ngIf="currentObject.typeName === 'job'; else link">
        <app-task-objects [object]="currentObject"></app-task-objects>
      </ng-container>
      <ng-template #link>
        <a [routerLink]="['/', currentObject.provider_id ? 'provider' : 'bundle', currentObject.provider_id || currentObject.bundle_id || {}]">
          {{ currentObject.provider_name || '' }}
          {{ currentObject.typeName === 'host' ? '' : currentObject.prototype_display_name || currentObject.prototype_name }}
          {{ currentObject.typeName === 'host' ? '' : currentObject.prototype_version }}
        </a>
      </ng-template>
    </ng-container>
  `,
})
export class SubtitleComponent {
  currentObject: IDetails;

  @Input() set current(currentInput: IDetails) {
    if (currentInput) {
      this.currentObject = currentInput;
    }
  }

}
