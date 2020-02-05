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

import { IStructure } from '../types';

@Component({
  selector: 'app-scheme',
  templateUrl: './scheme.component.html',
  styleUrls: ['./scheme.component.scss']
})
export class SchemeComponent implements OnInit {
  @Input() form: FormGroup;
  @Input() options: IStructure;

  value: any;
  rules: Array<any>;

  name: string;
  type: string;
  items: any[];

  currentType: string;

  constructor() {}

  ngOnInit() {
    this.value = this.options.value;

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
      this.items = (this.options.value as Array<any>).map(a => {
        return { value: a, rules: this.rules };       
      });
    } else if (this.currentType === 'dict') {

       this.items = Object.keys(this.value).map(b => {
          const c = this.findRule(b);
          return {value: this.value[b], rules: c};
        });
    } else {
      
    }
  }

  findRule(key: string) {
    return this.rules.find(a => a.name === key);
  }
}
