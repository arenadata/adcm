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
import { Component, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { AbstractControl, FormArray, FormGroup } from '@angular/forms';
import { FieldDirective } from '@app/shared/form-elements/field.directive';

import { IYContainer, IYField, matchType, YspecService } from '../yspec/yspec.service';

@Component({
  selector: 'app-scheme',
  styles: [
    `
      div.main {
        flex: 1;
      }
      .error {
        display: block;
        margin: -20px 0 6px 10px;
      }
    `,
  ],
  template: `<div class="main">
    <app-root-scheme #root [form]="currentFormGroup" [isReadOnly]="isReadOnly" [options]="rules" [value]="defaultValue"></app-root-scheme>
    <mat-error *ngIf="hasError('required')" class="error">Field [{{ field.display_name }}] is required!</mat-error>
  </div>`,
})
export class SchemeComponent extends FieldDirective implements OnInit, OnChanges {
  currentFormGroup: FormGroup | FormArray;
  rules: IYField | IYContainer;
  defaultValue: any;
  isReadOnly = false;
  initialField: AbstractControl;

  constructor(private yspec: YspecService) {
    super();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!changes.form.firstChange) {
      this.field.limits.rules = this.rules;
      this.defaultValue = this.field.value;
      this.resetForm();
    }
  }

  ngOnInit() {
    this.isReadOnly = this.field.read_only;
    this.yspec.Root = this.field.limits.yspec;
    this.rules = this.yspec.build();
    this.field.limits.rules = this.rules;

    this.defaultValue = this.field.value || this.field.default;
    this.initialField = this.form.controls[this.field.name];
    if (this.defaultValue !== null) this.resetForm();
    this.rules.name = '';
  }

  // validator() {
  //   const isEmptyArray = (v: any) => (Array.isArray(v) && v.length ? v.some((a) => isEmptyValue(a)) : false);
  //   const isEmptyObj = (v: any) => (isObject(v) && Object.keys(v).length ? Object.keys(v).some((a) => isEmptyValue(v[a])) : false);
  //   const isEmptyValue = (v: any) => !v || (Array.isArray(v) && !v.length) || (isObject(v) && !Object.keys(v).length) || isEmptyArray(v) || isEmptyObj(v);
  //   return (): ValidatorFn => (control: AbstractControl): { [key: string]: any } | null => (isEmptyValue(control.value) ? { isEmpty: true } : null);
  // }

  resetForm() {
    this.currentFormGroup = this.currentFormGroup || this.resetFormGroup(this.rules.type, this.field.name, this.form);
    //return this.currentFormGroup;
  }

  resetFormGroup(type: matchType, name: string, parent: FormGroup) {
    const form = type === 'list' ? new FormArray([]) : new FormGroup({});
    parent.setControl(name, form);
    return form;
  }

  /** this is using for restore default value */
  reload() {
    this.defaultValue = this.field.default;
    this.initialField.setValue(this.defaultValue);   
    this.form.setControl(this.field.name, this.initialField);
    this.currentFormGroup = undefined;
    if (this.defaultValue !== null) this.resetForm();
  }
}
