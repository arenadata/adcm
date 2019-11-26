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
import { Component, OnInit, Input } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { FieldOptions } from '@app/core/types';
import { debounceTime } from 'rxjs/internal/operators/debounceTime';

@Component({
  selector: 'app-fields-json',
  template: `
    <ng-container [formGroup]="form">
      <label>{{ field.label }}:</label>
      <mat-form-field class="full-width" [floatLabel]="'never'">
        <div style="margin-bottom: 4px;">
          <mat-error *ngIf="!isValid">
            <mat-error *ngIf="hasError('required')">Field [{{ field.label }}] is required!</mat-error>
            <mat-error *ngIf="hasError('jsonParseError') && (form.touched || form.dirty)">Json parsing error!</mat-error>
          </mat-error>
        </div>
        <div class="textarea-wrapper">
          <textarea
            style="flex-basis: auto;"
            [appMTextarea]="field.key"
            matInput
            class="full-width json_field"
            [formControlName]="field.key"
            [readonly]="field.disabled"
          ></textarea>         
        </div>
      </mat-form-field>
      <span class="info"><mat-icon matSuffix *ngIf="field.description" [appTooltip]="field.description">info_outline</mat-icon></span>
    </ng-container>
  `,
  styleUrls: ['./scss/fields.component.scss', './scss/json.scss'],
})
export class JsonComponent implements OnInit {
  @Input() form: FormGroup;
  @Input() field: FieldOptions;

  ngOnInit() {
    const control = this.form.controls[this.field.key];
    control.valueChanges.pipe(debounceTime(500)).subscribe(value => {
      try {
        const v = JSON.parse(value);
        control.setValue(JSON.stringify(v, undefined, 4));
      } catch (e) {}
    });
  }

  get isValid() {
    const field = this.form.controls[this.field.key];
    return field.disabled || (field.valid && (field.dirty || field.touched));
  }

  hasError(name: string) {
    return this.form.controls[this.field.key].hasError(name);
  }
}
