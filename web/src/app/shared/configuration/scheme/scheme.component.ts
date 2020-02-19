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
import { FormGroup } from '@angular/forms';
import { IStructure } from '../yspec/yspec.service';


@Component({
  selector: 'app-scheme',
  templateUrl: './scheme.component.html',
  styleUrls: ['./scheme.component.scss']
})
export class SchemeComponent implements OnInit {
  @Input() form: FormGroup;
  @Input() options: IStructure;

  value: any;
  rules: any;

  name: string;
  type: string;
  items: any[];

  currentType: string;

  constructor() {}

  ngOnInit() {
    this.value = this.options.value;

    // const currentFormGroup = this.options.key
    //   .split('/')
    //   .reverse()
    //   .reduce((p, c) => p.get(c), this.form) as FormGroup;

    const current = this.options.rules;
    this.currentType = this.options.rules.type;

    Object.keys(current).map(key => {
      if (key === 'type') this.type = this.options.rules[key];
      else {
        this.name = key;
        this.rules = current[key];
      }
    });

    if (this.currentType === 'list') {
      // currentFormGroup.addControl('array', new FormArray([]));
      this.items = (this.options.value as Array<any>).map(a => {
        return { value: a, rules: this.rules };
      });
    } else if (this.currentType === 'dict') {
      this.items = Object.keys(this.value).map(b => {
        const c = this.findRule(b);
        
        // if (c.type !== 'list' && c.type !== 'dict') currentFormGroup.addControl(b, new FormControl(this.value[b]));

        return { value: this.value[b], rules: c };
      });
    } else {
    }
  }

  findRule(key: string) {
    return this.rules.find(a => a.name === key) || this.rules.find(a => Object.keys(a).find(k => k === key));
  }

  add() {
    if (this.type === 'list') {
      if (this.rules.type === 'dict') {
        const [type, rule] = Object.keys(this.rules);
        const value = this.rules[rule].reduce((p, c) => {
          p[c.name] = '';
          return p;
        }, {});
        this.items.push({ value, rules: this.rules });
      }
      if (this.rules.type !== 'dict' && this.rules.type !== 'list') this.items.push({ value: `new ${this.items.length + 1}`, rules: this.rules });
    }
    if (this.type === 'dict') {
    }
  }

  remove(i: number) {
    this.items = this.items.filter((v, ind) => ind !== i);
  }

  trackByFn(index, item) {
    return index; // or item.id
  }
}
