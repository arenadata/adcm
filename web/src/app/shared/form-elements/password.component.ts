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
  selector: 'app-fields-password',
  template: `
    <ng-container [formGroup]="form">
      <div>
        <label>{{ field.label }}:</label>
        <mat-form-field class="full-width" [floatLabel]="'never'">
          <input matInput (input)="confirmPasswordFieldUpdate()" [formControlName]="field.key" type="password" [readonly]="field.disabled" />
          <mat-error *ngIf="!isValid"> Field [{{ field.label }}] is required! </mat-error>
        </mat-form-field>
        <span class="info"
          ><mat-icon *ngIf="field.description" matSuffix [appTooltip]="field.description">
            info_outline
          </mat-icon></span
        >
      </div>
      <div *ngIf="getConfirmPasswordField()">
        <label>confirm [ {{ field.label }} ]:</label>
        <mat-form-field class="full-width" [floatLabel]="'never'">
          <input matInput appConfirmEqualValidator="{{ field.key }}" [formControlName]="'confirm_' + field.key" type="password" [readonly]="field.disabled" />
          <mat-error *ngIf="getConfirmPasswordFieldErrors('required') && (form.touched || form.dirty)"> Confirm [{{ field.label }}] is required! </mat-error>
          <mat-error *ngIf="getConfirmPasswordFieldErrors('notEqual') && (form.touched || form.dirty)">
            Field [{{ field.label }}] and confirm [{{ field.label }}] does not match!
          </mat-error>
        </mat-form-field>
        <span class="info"></span>
      </div>
    </ng-container>
  `,
  styleUrls: ['./scss/fields.component.scss', './scss/password.scss']
})
export class PasswordComponent extends FieldDirective {
  getConfirmPasswordField() {
    return this.form.controls['confirm_' + this.field.key];
  }

  confirmPasswordFieldUpdate() {
    const confirm = this.getConfirmPasswordField();
    return confirm ? confirm.updateValueAndValidity() : '';
  }

  getConfirmPasswordFieldErrors(error: string) {
    const confirm = this.getConfirmPasswordField();
    if (confirm && confirm.errors) {
      return confirm.errors[error];
    }
    return null;
  }
}
