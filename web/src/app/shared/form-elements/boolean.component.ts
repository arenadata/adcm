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
import { MAT_CHECKBOX_DEFAULT_OPTIONS } from '@angular/material/checkbox';

import { FieldDirective } from './field.directive';

const options = { clickAction: 'noop', color: 'accent' };

@Component({
  selector: 'app-fields-boolean',
  template: `
    <ng-container [formGroup]="form">
      <mat-checkbox [formControlName]="field.name" [indeterminate]="field.value === null" (click)="cbChange()"></mat-checkbox>
      <mat-error *ngIf="!isValid"><app-error-info [field]="field" [control]="control"></app-error-info></mat-error>
    </ng-container>
  `,
  styles: [':host {height: 58px;} mat-error { font-size: 0.75em; margin-left: 14px; }'],
  providers: [{ provide: MAT_CHECKBOX_DEFAULT_OPTIONS, useValue: options }]
})
export class BooleanComponent extends FieldDirective {
  cbChange() {
    if (this.field.read_only) return;
    const tape = this.field.validator.required ? [true, false] : [null, true, false];
    this.field.value = tape[(tape.indexOf(this.field.value as boolean) + 1) % tape.length];
    this.control.setValue(this.field.value);
  }
}
