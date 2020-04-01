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
import { FormArray, FormControl, FormGroup } from '@angular/forms';

import { FieldService } from '../field.service';
import { IYContainer, matchType, IYField, reqursionType } from '../yspec/yspec.service';

type sValue = string | boolean | number;

export interface IValue {
  [key: string]: sValue;
}

export interface IControl {
  name: string;
  type: matchType;
  rules: IYField | IYContainer | (IYField | IYContainer)[];
  form: FormGroup | FormArray;
  value: IValue | sValue;
  parent: reqursionType;
}

@Component({
  selector: 'app-root-scheme',
  templateUrl: './root.component.html',
  styleUrls: ['./root.component.scss']
})
export class RootComponent implements OnInit {
  @Input() form: FormGroup | FormArray;
  @Input() options: IYContainer | IYField;
  @Input() value: IValue | IValue[];
  @Input() isReadOnly = false;

  controls: IControl[] = [];

  constructor(private service: FieldService) {}

  ngOnInit(): void {
    if (this.value) {
      if (this.options.type === 'list' && Array.isArray(this.value)) {
        const value = this.value as IValue[];
        value.map((x, i) => this.add([i.toString(), x]));
      } else if (typeof this.value === 'object') {
        Object.keys(this.value).map(x => this.add([x, this.value[x]]));
      }
    }
  }

  showControls() {
    return !this.isReadOnly && (this.options.type === 'list' || this.options.type === 'dict');
  }

  remove(i: number) {
    if (Array.isArray(this.form.controls)) {
      (this.form as FormArray).removeAt(i);
      this.controls = this.controls.filter((a, n) => n !== i);
    }
  }

  add(v: [string, IValue | sValue] = ['', '']) {
    let [name, value] = v;

    if ((this.rules as IYContainer).type === 'dict') {
      const rules = this.itemRules;

      if (!value) value = rules.reduce((p, c) => ({ ...p, [c.name]: '' }), {});

      if (this.checkValue(value, rules)) {
        const form = new FormGroup({});
        (this.form as FormArray).push(form);
        const item: IControl = { name, value, type: (this.rules as IYContainer).type, rules, form, parent: 'list' };
        this.controls = [...this.controls, item];
      }
    } else {
      const rules = Array.isArray(this.rules) ? this.rules.find(a => a.name === name) : this.rules;

      if (rules) {
        let form: FormGroup | FormArray;
        if (rules.type !== 'list' && rules.type !== 'dict') {
          const { validator, controlType } = rules as IYField;

          if (Array.isArray(this.form.controls)) {
            name = this.form.controls.length.toString();
            (this.form as FormArray).push(new FormControl(value || '', this.service.setValidator({ validator, controlType })));
          } else
            (this.form as FormGroup).addControl(rules.name, new FormControl(rules.type !== 'bool' ? value || '' : value, this.service.setValidator({ validator, controlType })));
          form = this.form;
        } else {
          if (rules.type === 'list') form = new FormArray([]);
          if (rules.type === 'dict') form = new FormGroup({});
          (this.form as FormGroup).addControl(rules.name, form);
        }
        const item: IControl = { name, value, type: rules.type, rules, form, parent: this.options.type as reqursionType };
        this.controls = [...this.controls, item];
      }
    }
  }

  checkValue(value: IValue | sValue, rules: (IYField | IYContainer)[]) {
    if (!value) return false;
    if (Array.isArray(rules)) {
      if (Array.isArray(value)) {
        return rules.some(a => a.name === value[0]);
      } else if (typeof value === 'object') {
        return Object.keys(value).every(x => rules.some(a => a.name === x));
      }
    }
  }

  get rules(): IYField | IYContainer | (IYField | IYContainer)[] {
    if ('options' in this.options) return this.options.options;
    else return this.options;
  }

  get itemRules(): (IYField | IYContainer)[] {
    return (this.rules as IYContainer).options as (IYField | IYContainer)[];
  }

  trackByFn(index: number) {
    return index;
  }
}
