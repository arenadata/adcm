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
import { ChangeDetectorRef, Component, Input, OnInit } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { isObject } from '@app/core/types';

import { FieldOptions } from '../types';

@Component({
  selector: 'app-field',
  templateUrl: './field.component.html',
  styleUrls: ['./field.component.scss']
})
export class FieldComponent implements OnInit {
  @Input()
  options: FieldOptions;
  @Input()
  form: FormGroup;

  currentFormGroup: FormGroup;

  constructor(public cdetector: ChangeDetectorRef) {}

  ngOnInit() {
    const [name, ...other] = this.options.key.split('/');
    this.currentFormGroup = other.reverse().reduce((p, c) => p.get(c), this.form) as FormGroup;
    return this.currentFormGroup;
  }

  getTestName() {
    return `${this.options.name}${this.options.subname ? '/' + this.options.subname : ''}`;
  }

  outputValue(value: any) {
    const v = isObject(value) ? JSON.stringify(value) : value + '';
    return v.length > 80 ? v.substr(0, 80) + '...' : v;
  }

  outputTooltip(value: any) {
    const v = isObject(value) ? JSON.stringify(value) : value + '';
    return v.length > 80 ? v : '';
  }

  isAdvanced() {
    return this.options.ui_options && this.options.ui_options.advanced;
  }

  restore() {
    const field = this.currentFormGroup.controls[this.options.name];
    const value = this.options.default;
    const type = this.options.type;
    if (field) {
      if (type === 'json') {
        field.setValue(value === null ? '' : JSON.stringify(value, undefined, 4));
      } else if (type === 'boolean') {
        const allow = String(value) === 'true' || String(value) === 'false' || String(value) === 'null';
        field.setValue(allow ? value : null);
      } else if (type === 'password') {
        field.setValue(value);
        field.updateValueAndValidity();

        const confirm = this.currentFormGroup.controls[`confirm_${this.options.name}`];
        if (confirm) {
          confirm.setValue(value);
          confirm.updateValueAndValidity();
        }
      } else if (type === 'structure') {
      } else field.setValue(value);
      this.options.value = field.value;
    }
  }
}
