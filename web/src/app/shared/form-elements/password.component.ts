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
import { Component, OnInit } from '@angular/core';
import { FormControl } from '@angular/forms';

import { FieldService } from './../configuration/field.service';
import { FieldDirective } from './field.directive';

@Component({
  selector: 'app-fields-password',
  template: `
    <ng-container [formGroup]="form">
      <mat-form-field>
        <input matInput (input)="confirmPasswordFieldUpdate()" [formControlName]="field.name" type="password" [readonly]="field.read_only" />
        <mat-error *ngIf="hasError('required')"> Field [{{ field.display_name }}] is required! </mat-error>
      </mat-form-field>
      <mat-form-field *ngIf="getConfirmPasswordField()">
        <input matInput [formControlName]="'confirm_' + field.name" type="password" [readonly]="field.read_only" />
        <mat-error *ngIf="hasErrorConfirm('required')"> Confirm [{{ field.display_name }}] is required! </mat-error>
        <mat-error *ngIf="hasErrorConfirm('notEqual')"> Field [{{ field.display_name }}] and confirm [{{ field.display_name }}] does not match! </mat-error>
      </mat-form-field>
    </ng-container>
  `,
  styleUrls: ['./password.component.scss'],
})
export class PasswordComponent extends FieldDirective implements OnInit {
  constructor(private service: FieldService) {
    super();
  }

  ngOnInit() {
    if (!this.field.ui_options?.no_confirm) {
      this.form.addControl(`confirm_${this.field.name}`, new FormControl(this.field.value, this.field.activatable ? [] : this.service.setValidator(this.field, this.control)));
    }

    super.ngOnInit();

    const confirm = this.getConfirmPasswordField();
    if (confirm) confirm.markAllAsTouched();
  }

  getConfirmPasswordField() {
    return this.form.controls['confirm_' + this.field.name];
  }

  hasErrorConfirm(name: string) {
    const c = this.getConfirmPasswordField();
    return this.getConfirmPasswordFieldErrors(name) && (c.touched || c.dirty);
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
