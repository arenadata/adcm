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
import { MAT_CHECKBOX_CLICK_ACTION, MatCheckbox } from '@angular/material/checkbox';

import { FieldDirective } from './field.directive';

@Component({
  selector: 'app-fields-boolean',
  template: `
    <ng-container [formGroup]="form">
      <label [appTooltip]="field.display_name" [appTooltipShowByCondition]="true">{{ field.display_name }}:</label>
      <div class="full-width">
        <div>
          <mat-checkbox [labelPosition]="'before'" [formControlName]="field.name" [indeterminate]="field.value === null" (click)="cbChange()"></mat-checkbox>
          <span class="info">
            <mat-icon [ngClass]="'info-icon'" *ngIf="field.description" matSuffix [appTooltip]="field.description">info_outline</mat-icon>
            <button mat-icon-button matSuffix (click)="restore()" color="primary" [appTooltip]="'Reset to default'"><mat-icon>refresh</mat-icon></button>
          </span>
        </div>
        <mat-error *ngIf="!isValid">Field [ {{ field.display_name }} ] is required!</mat-error>
      </div>
    </ng-container>
  `,
  styleUrls: ['./scss/fields.component.scss', './scss/boolean.scss'],
  providers: [{ provide: MAT_CHECKBOX_CLICK_ACTION, useValue: 'noop' }]
})
export class BooleanComponent extends FieldDirective {
  cbChange() {
    if (this.field.disabled) return;
    const tape = this.field.validator.required ? [true, false] : [null, true, false];
    this.field.value = tape[(tape.indexOf(this.field.value as boolean) + 1) % tape.length];
    const field = this.find();
    field.setValue(this.field.value);
  }
}
