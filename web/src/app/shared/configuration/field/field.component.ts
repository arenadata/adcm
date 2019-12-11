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
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, Input } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { FieldOptions, FieldStack, isObject } from '@app/core/types';

import { CompareConfig } from '../field.service';

interface Compare {
  config: CompareConfig;
  stack: FieldStack;
}

@Component({
  selector: 'app-field',
  templateUrl: './field.component.html',
  styleUrls: ['./field.component.scss'],
  //changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FieldComponent {
  @Input()
  options: FieldOptions;
  @Input()
  form: FormGroup;

  compare: Compare[] = [];

  constructor(public cdetector: ChangeDetectorRef) {}

  getTestName() {
    return `${this.options.name}${this.options.subname ? '/' + this.options.subname : ''}`;
  }

  addCompare(c: { config: CompareConfig; stack: FieldStack }) {
    if (!this.compare.some(a => a.config.id === c.config.id && a.stack.name === c.stack.name)) this.compare.push(c);
  }

  outputValue(value: any) {
    const v = isObject(value) ? JSON.stringify(value) : value + '';
    return v.length > 80 ? v.substr(0, 80) + '...' : v;
  }

  outputTooltip(value: any) {
    const v = isObject(value) ? JSON.stringify(value) : value + '';
    return v.length > 80 ? v : '';
  }

  clearCompare(c: number[]) {
    this.compare = this.compare.filter(a => c.includes(a.config.id));
  }

  isAdvanced() {
    return this.options.ui_options && this.options.ui_options.advanced;
  }

  // for all children
  // TODO: https://angular.io/guide/dependency-injection-navtree
  get isValid() {
    const field = this.form.controls[this.options.key];
    return field.disabled || (field.valid && (field.dirty || field.touched));
  }

  hasError(name: string) {
    return this.form.controls[this.options.key].hasError(name);
  }
}
