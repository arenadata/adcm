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
  selector: 'app-fields-textbox',
  template: `
    <ng-container [formGroup]="form">
      <label [appTooltip]="field.display_name" [appTooltipShowByCondition]="true">{{ field.display_name }}:</label>
      <mat-form-field class="full-width" [floatLabel]="'never'">
        <input matInput [formControlName]="field.name" [readonly]="field.disabled" [type]="field.type" />
        <mat-error *ngIf="!isValid">
          <mat-error *ngIf="hasError('required')">Field [{{ field.display_name }}] is required!</mat-error>
          <mat-error *ngIf="hasError('pattern')">Field [{{ field.display_name }}] is invalid!</mat-error>
          <mat-error *ngIf="hasError('min')">Field [{{ field.display_name }}] value cannot be less than {{ field.validator.min }}!</mat-error>
          <mat-error *ngIf="hasError('max')">Field [{{ field.display_name }}] value cannot be greater than {{ field.validator.max }}!</mat-error>
        </mat-error>
      </mat-form-field>
      <span class="info"><mat-icon *ngIf="field.description" matSuffix [appTooltip]="field.description">info_outline</mat-icon></span>
    </ng-container>
  `,
  styleUrls: ['./scss/fields.component.scss']
})
export class TextBoxComponent extends FieldDirective {}
