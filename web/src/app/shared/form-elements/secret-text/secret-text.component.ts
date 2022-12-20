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
import { FormControl, Validators } from '@angular/forms';

@Component({
  selector: 'app-fields-secret-text',
  templateUrl: './secret-text.component.html',
})
export class SecretTextComponent extends FieldDirective implements OnInit, OnChanges {
  dummy = '********';
  dummyControl: FormControl;
  value: string;

  ngOnChanges(): void {
    this.value = this.field.value as string;

    this.control.statusChanges.pipe(this.takeUntil()).subscribe((status) => {
      if (status === 'DISABLED') {
        this.dummyControl.disable();
        this.dummyControl.markAsUntouched();
        this.control.markAsUntouched();
      } else {
        this.dummyControl.enable();
        this.dummyControl.markAsTouched();
        this.control.markAsTouched();
      }
    });
  }

  ngOnInit(): void {
    this._initDummyControl();
  }

  onBlur(): void {
    this.control.setValue(this.dummyControl.value || this.value);
    this.dummyControl.setValue(this.dummyControl.value ? this.dummy : '');
  }

  onFocus(): void {
    this.dummyControl.setValue(null);
  }

  clear(): void {
    this.dummyControl.setValue(null);
  }

  private _initDummyControl(): void {
    this.dummyControl = new FormControl(
      { value: this.control.value ? this.dummy : '', disabled: this.control.disabled },
      Validators.compose(this.field.required ? [Validators.required] : [])
    );
    this.dummyControl.markAllAsTouched();
  }

}
