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
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { DynamicComponent, DynamicEvent } from '@app/shared/directives/dynamic.directive';

@Component({
  selector: 'app-dumb',
  template: '<mat-card-content class="content" [innerHTML]="model?.html"></mat-card-content>',
  styles: [
    // '.content { overflow: auto; max-height: 40vh;}',
    // Firefox not working : main.component.html line: 4
    // '.content { overflow: auto; height: -moz-available; height: -webkit-fill-available; height: fill-available;}',
  ],
})
export class DumbComponent implements DynamicComponent {
  @Output() event = new EventEmitter<DynamicEvent>();
  @Input() model?: any;
}
