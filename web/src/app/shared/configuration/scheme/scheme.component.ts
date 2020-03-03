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

import { YspecService } from '../yspec/yspec.service';

@Component({
  selector: 'app-scheme',
  template: '<app-root-scheme [form]="itemFormGroup" [options]="rules" [value]="defaultValue"></app-root-scheme>'
})
export class SchemeComponent implements OnInit {
  @Input() form: FormGroup;
  @Input() options: any;

  itemFormGroup: FormGroup | FormArray;
  rules: any;
  defaultValue: any;

  constructor(private yspec: YspecService) {}

  ngOnInit() {
    this.yspec.Root = this.options.limits.yspec;
    this.rules = this.yspec.build();
    this.options.limits.rules = this.rules;
    this.itemFormGroup = this.options.key
      .split('/')
      .reverse()
      .reduce((p: any, c: string) => p.get(c), this.form) as FormGroup;

    this.defaultValue = this.options.value || this.options.default;

    if (this.rules.type === 'list') {
      const parent = this.itemFormGroup.parent as FormGroup;
      parent.removeControl(this.options.name);
      this.itemFormGroup = new FormArray([]);
      parent.addControl(this.options.name, this.itemFormGroup);
    }
    this.rules.name = this.options.name;
  }
}
