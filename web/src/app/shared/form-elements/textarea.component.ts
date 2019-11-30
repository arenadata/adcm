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
import { Component } from '@angular/core';

import { FieldDirective } from './field.directive';

@Component({
  selector: 'app-fields-textarea',
  template: `
    <ng-container [formGroup]="form">
      <label>{{ field.label }}:</label>
      <mat-form-field class="full-width" [floatLabel]="'never'">
        <mat-error *ngIf="!isValid">
          <mat-error *ngIf="hasError('required')">Field [{{ field.label }}] is required!</mat-error>
          <mat-error *ngIf="hasError('pattern')">Field [{{ field.label }}] is invalid!</mat-error>
          <mat-error *ngIf="hasError('min')">Field [{{ field.label }}] value cannot be less than {{ field.validator.min }}!</mat-error>
          <mat-error *ngIf="hasError('max')">Field [{{ field.label }}] value cannot be greater than {{ field.validator.max }}!</mat-error>
        </mat-error>
        <div class="textarea-wrapper">
          <textarea matInput class="full-width json_field" [appMTextarea]="field.key" [formControlName]="field.key" [readonly]="field.disabled"></textarea>
        </div>
      </mat-form-field>
      <span class="info"><mat-icon matSuffix *ngIf="field.description" [appTooltip]="field.description"> info_outline</mat-icon></span>
    </ng-container>
  `,
  styleUrls: ['./scss/fields.component.scss', './scss/json.scss']
})
export class TextareaComponent extends FieldDirective {}
