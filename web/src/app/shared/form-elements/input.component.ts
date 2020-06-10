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
import { BaseDirective } from '../directives';

@Component({
  selector: 'app-input',
  template: `
    <div class="row" [formGroup]="form">
      <mat-form-field class="full-width">
        <input matInput [placeholder]="label" formControlName="{{ controlName }}" [required]="isRequired" />
        <mat-error *ngIf="isError(controlName)">
          <mat-error *ngIf="hasError(controlName, 'required')">{{ label }} is required.</mat-error>
          <mat-error *ngIf="hasError(controlName, 'pattern')">{{ label }} is not correct.</mat-error>
        </mat-error>
      </mat-form-field>
    </div>
  `,
  styles: ['.row {display:flex;}'],
})
export class InputComponent extends BaseDirective {
  @Input() form: FormGroup;
  @Input() controlName: string;
  @Input() label: string;
  @Input() isRequired = false;

  isError(name: string) {
    const f = this.form.get(name);
    return f.invalid && (f.dirty || f.touched);
  }

  hasError(name: string, error: string) {
    return this.form.controls[name].hasError(error);
  }
}
