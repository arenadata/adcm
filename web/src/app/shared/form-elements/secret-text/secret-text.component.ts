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
import { Component, OnChanges, OnInit, } from '@angular/core';

import { FieldDirective } from '../field.directive';
import { FormControl } from '@angular/forms';

@Component({
  selector: 'app-fields-secret-text',
  templateUrl: './secret-text.component.html',
})
export class SecretTextComponent extends FieldDirective implements OnInit, OnChanges {
  dummy = '********';
  dummyControl: FormControl;
  value: string;

  get control(): FormControl {
    return this.dummyControl;
  }

  ngOnChanges(): void {
    this.value = this.field.value as string;
  }

  ngOnInit(): void {
    this._initDummyControl();
  }

  onBlur(): void {
    this.form.controls[this.field.name].setValue(this.control.value);
    this.control.setValue(this.dummy);
  }

  onFocus(): void {
    this.control.setValue(null);
  }

  private _initDummyControl(): void {
    this.dummyControl = new FormControl(this.dummy);
    this.control.markAllAsTouched();
  }

}
