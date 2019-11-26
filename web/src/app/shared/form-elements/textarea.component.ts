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
import { FormGroup } from '@angular/forms';
import { FieldOptions } from '@app/core/types';

@Component({
  selector: 'app-fields-textarea',
  template: `
    <ng-container [formGroup]="form">
      <label>{{ field.label }}:</label>
      <mat-form-field class="full-width" [floatLabel]="'never'">
        <div class="textarea-wrapper">
          <textarea matInput class="full-width json_field" [appMTextarea]="field.key" [formControlName]="field.key" [readonly]="field.disabled">
          {{ field.value }}
          </textarea>          
        </div>
        <mat-error *ngIf="!isValid">Field {{ field.label }} is required or invalid!</mat-error>
      </mat-form-field>
      <span class="info"><mat-icon matSuffix *ngIf="field.description" [appTooltip]="field.description"> info_outline</mat-icon></span>
    </ng-container>
  `,
  styleUrls: ['./scss/fields.component.scss', './scss/json.scss'],
})
export class TextareaComponent {
  @Input() form: FormGroup;
  @Input() field: FieldOptions;

  get isValid() {
    const field = this.form.controls[this.field.key];
    return field.disabled || (field.valid && (field.dirty || field.touched));
  }
}
