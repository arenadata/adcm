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
import { AbstractControl, FormArray, FormControl, FormGroup } from '@angular/forms';

import { FieldService } from '../field.service';

@Component({
  selector: 'app-root-scheme',
  templateUrl: './root.component.html',
  styleUrls: ['./root.component.scss']
})
export class RootComponent implements OnInit {
  @Input() form: FormGroup | FormArray;
  @Input() options: any;
  @Input() value: any;

  controls: { name: string; type: string; rules: any; form: FormGroup | FormArray; value: any }[] = [];

  constructor(private service: FieldService) {}

  ngOnInit(): void {
    if (this.value) {
      if (this.options.type === 'list' && Array.isArray(this.value)) {
        const value = this.value as any[];
        value.map((x: { [key: string]: any }, i: number) => this.add([i.toString(), x]));
      } else if (typeof this.value === 'object') {
        Object.keys(this.value).map(x => this.add([x, this.value[x]]));
      }
    }
  }

  notSimple(item: AbstractControl) {
    return 'controls' in item;
  }

  notSimpleDict(item) {
    return item.type === 'list' || item.type === 'dict';
  }

  getForm(item) {
    return (this.form as FormGroup).controls[item.name];
  }

  remove(i: number) {
    (this.form as FormArray).removeAt(i);
    this.controls = this.controls.filter((a, n) => n !== i);
  }

  add(v: [string, string | boolean | number | { [key: string]: any }] = ['', null]) {
    let [name, value] = v;

    if (this.rules.type === 'dict') {
      if (!value) {
        value = this.itemRules.reduce((p, c) => {
          p[c.name] = '';
          return p;
        }, {});
      }

      if (this.checkValue(value, this.itemRules)) {
        const form = new FormGroup({});
        (this.form as FormArray).push(form);
        this.controls.push({ name, value, type: this.rules.type, rules: this.itemRules, form });
      }
    } else if (this.checkValue(v, this.rules)) {
      const rule = Array.isArray(this.rules) ? this.rules.find(a => a.name === name) : this.rules;
      if (rule) {
        let form: FormGroup | FormArray;
        if (rule.type !== 'list' && rule.type !== 'dict') {
          if (Array.isArray(this.form.controls)) (this.form as FormArray).push(new FormControl(value || '', this.service.setValidator(rule)));
          else (this.form as FormGroup).addControl(rule.name, new FormControl(value || '', this.service.setValidator(rule)));
          form = this.form;
        } else {
          if (rule.type === 'list') {
            form = new FormArray([]);
          }

          if (rule.type === 'dict') {
            form = new FormGroup({});
          }
          (this.form as FormGroup).addControl(rule.name, form);
        }
        const item = { name, value, type: rule.type, rules: rule, form };
        this.controls.push(item);
      }
    }
  }

  checkValue(value, rules) {
    if (!value) return true;
    if (Array.isArray(rules)) {
      if (Array.isArray(value)) {
        return rules.some(a => a.name === value[0]);
      } else if (typeof value === 'object') {
        return Object.keys(value).every(x => rules.some(a => a.name === x));
      }
    }
    // ????
    return true;
  }

  get rules() {
    return this.options.options ? this.options.options[0] : this.options;
  }

  get itemRules() {
    return this.rules.options[0];
  }

  get isValid() {
    return true;
  }

  hasError(title: string) {}

  trackByFn(index, item) {
    return index; // or item.id
  }

}
