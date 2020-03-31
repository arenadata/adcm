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
import { Directive, Input, OnInit } from '@angular/core';
import { FormGroup } from '@angular/forms';

import { FieldOptions } from '../configuration/types';
import { BaseDirective } from '../directives';

@Directive({
  selector: '[appField]'
})
export class FieldDirective extends BaseDirective implements OnInit {
  @Input() form: FormGroup;
  @Input() field: FieldOptions;

  ngOnInit() {
    const field = this.find();
    field.markAsTouched();
  }

  find() {
    return this.form.controls[this.field.name];
  }

  get control() {
    return this.form.controls[this.field.name];
  }

  get isValid() {
    const field = this.find();
    return this.field.read_only || (field.valid && (field.dirty || field.touched));
  }

  hasError(name: string) {
    return this.find().hasError(name);
  }
}
