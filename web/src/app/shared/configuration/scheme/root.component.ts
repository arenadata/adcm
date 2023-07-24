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
import { Component, Input, OnInit } from '@angular/core';
import { FormArray, FormGroup } from '@angular/forms';

import { TNReq, TValue } from '../types';
import { IYContainer, IYField } from '../yspec/yspec.service';
import { IControl, IValue, SchemeService } from './scheme.service';

@Component({
  selector: 'app-root-scheme',
  templateUrl: './root.component.html',
  styleUrls: ['./root.component.scss'],
})
export class RootComponent implements OnInit {
  @Input() form: FormGroup | FormArray;
  @Input() options: IYContainer | IYField;
  @Input() value: TValue;
  @Input() isReadOnly = false;
  @Input() invisibleItems: string[];

  controls: IControl[] = [];

  constructor(private scheme: SchemeService) {}

  init() {
    if (this.value) {
      if (Array.isArray(this.value)) {
        this.value.forEach((value, index) => {
          this.itemRules?.forEach((key) => {
            if (!value[key.name]) {
              value[key.name] = key.type === 'string' ? '' : key.type === 'integer' ? 0 : null;
            }
          })
        })
      }

      if (this.options.type === 'list' && Array.isArray(this.value)) {
        (this.value as IValue[]).forEach((x, i) => this.add(['', x]));
      } else if (typeof this.value === 'object') {
        Object.keys(this.value).forEach((x) => this.add([x, this.value[x]]));
      }
    } else if (this.options.type === 'dict' && Array.isArray(this.options.options)) {
      this.options.options.forEach((x) => this.add([x.name, '']));
    }
  }

  ngOnInit(): void {
    this.init();
  }

  reload(value: TValue) {
    this.value = value;
    this.controls.length = 0;

    if (Array.isArray(this.form.controls)) {
      while (this.form.controls.length > 0) {
        (this.form as FormArray).removeAt(0);
      }
    } else if (this.form.controls && typeof this.form.controls === 'object') {
      Object.keys(this.form.controls).forEach((key) => {
        while (this.form.controls[key]?.controls.length > 0) {
          (this.form.controls[key] as FormArray).removeAt(0);
        }
        (this.form as FormGroup).removeControl(key);
      })
    }

    this.init();
  }

  add(v: [string, IValue | TValue] = ['', '']) {
    const [name, value] = v;
    const flag = (this.rules as IYContainer).type === 'dict';
    const item = flag
      ? this.scheme.addControlsDict(name, value, this.form as FormArray, this.itemRules as IYContainer[])
      : this.scheme.addControls(name, value, this.form, this.rules, this.options.type as TNReq);
    this.controls = [...this.controls, item];
    this.form.updateValueAndValidity();
  }

  showControls() {
    return !this.isReadOnly && (this.options.type === 'list' || this.options.type === 'dict');
  }

  remove(name: string | number) {
    if (Array.isArray(this.form.controls)) {
      (this.form as FormArray).removeAt(+name);
      this.controls = this.controls.filter((a, i) => (a.name ? a.name !== name : i !== +name));
      this.form.updateValueAndValidity();
    }
  }

  get rules(): IYField | IYContainer | (IYField | IYContainer)[] {
    if ('options' in this.options) return this.options.options;
    else return this.options;
  }

  get itemRules(): (IYField | IYContainer)[] {
    return (this.rules as IYContainer).options as (IYField | IYContainer)[];
  }
}
