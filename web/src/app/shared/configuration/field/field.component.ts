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
import { ChangeDetectorRef, Component, Input, OnInit, ViewChild } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { FieldDirective } from '@app/shared/form-elements/field.directive';
import { BaseMapListDirective } from '@app/shared/form-elements/map.component';

import { SchemeComponent } from '../scheme/scheme.component';
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

  @ViewChild('cc') inputControl: FieldDirective;

  constructor(public cdetector: ChangeDetectorRef) {}

  ngOnInit() {
    const [name, ...other] = this.options.key.split('/');
    this.currentFormGroup = other.reverse().reduce((p, c) => p.get(c), this.form) as FormGroup;
  }

  getTestName() {
    return `${this.options.name}${this.options.subname ? '/' + this.options.subname : ''}`;
  }

  outputValue(v: string, isPart = false) {
    return v.length > 80 ? (isPart ? v : `${v.substr(0, 80)}...`) : v;
  }

  isAdvanced() {
    return this.options.ui_options && this.options.ui_options.advanced;
  }

  restore() {
    const field = this.currentFormGroup.controls[this.options.name];
    const defaultValue = this.options.default;
    const type = this.options.type;
    if (field) {
      if (type === 'json') {
        field.setValue(defaultValue === null ? '' : JSON.stringify(defaultValue, undefined, 4));
      } else if (type === 'boolean') {
        const allow = String(defaultValue) === 'true' || String(defaultValue) === 'false' || String(defaultValue) === 'null';
        field.setValue(allow ? defaultValue : null);
      } else if (type === 'password') {
        field.setValue(defaultValue);
        field.updateValueAndValidity();

        const confirm = this.currentFormGroup.controls[`confirm_${this.options.name}`];
        if (confirm) {
          confirm.setValue(defaultValue);
          confirm.updateValueAndValidity();
        }
      } else if (type === 'map' || type === 'list') {
        this.options.value = defaultValue;
        (this.inputControl as BaseMapListDirective).reload();
        
      } else if (type === 'structure') {
        this.options.value = defaultValue;
        (this.inputControl as SchemeComponent).reload();
      } else field.setValue(defaultValue);

      this.options.value = field.value;
      this.form.updateValueAndValidity();
    }
  }
}
