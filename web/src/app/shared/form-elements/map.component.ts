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
import { Component, Directive, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { FormArray, FormBuilder, FormGroup, Validators } from '@angular/forms';

import { FieldDirective } from './field.directive';

@Directive({
  selector: '[appBaseMapList]'
})
export class BaseMapListDirective extends FieldDirective implements OnInit, OnChanges {
  asList: boolean;
  items = new FormArray([]);

  constructor(private fb: FormBuilder) {
    super();
  }

  ngOnChanges(changes: SimpleChanges) {
    this.control.statusChanges.pipe(
      this.takeUntil()
    ).subscribe((state) => {
      if (state === 'DISABLED') {
        this.items.controls.forEach((control) => {
          control.disable({ emitEvent: false });
          control.markAsUntouched();
        });
        this.control.markAsUntouched();
      } else {
        this.items.controls.forEach((control) => {
          control.enable({ emitEvent: false });
          control.markAsTouched();
        });
        this.control.markAsTouched();
      }
    });
  }

  ngOnInit() {
    if (!Object.keys(this.field.value || {}).length) this.control.setValue('');

    this.reload();
    this.items.valueChanges.pipe(
      this.takeUntil()
    ).subscribe((a: { key: string; value: string }[]) => {
      this.prepare(a)
    });
  }

  prepare(a: { key: string; value: string }[]) {
    let value = this.asList ? 
      a.map(b => b.value).filter(c => c) : 
      a.length && a.length > 0 ? 
        a.reduce((p, c) => ({
          ...p,
          [c.key]: c.value
        }), {}) : 
        null;

    if (value && this.asList) value = (value as Array<string>).length ? value : null;
    this.control.setValue(value);
    this.control.markAsTouched();
  }

  reload() {
    const fieldValue = this.field.value ? { ...(this.field.value as Object) } : null;

    if (!fieldValue) {
      this.items.clear();
    } else {
      this.items.reset([]);
      this.items.controls = [];

      Object.keys(fieldValue).forEach(a => this.items.push(
        this.fb.group({
          key: [{ value: a, disabled: this.control.disabled }, Validators.required],
          value: [{ value: fieldValue[a], disabled: this.control.disabled }],
        })
      ));
    }
  }

  add() {
    const group = this.fb.group({ key: ['', Validators.required], value: '' });
    this.items.push(group);
    group.controls['key'].markAsTouched();
  }

  check(item: FormGroup) {
    return item.controls['key'].hasError('required');
  }

  clear(i: number) {
    this.items.removeAt(i);
  }
}

@Component({
  selector: 'app-fields-list',
  templateUrl: './map-list.template.html',
  styleUrls: ['./map.component.scss']
})
export class FieldListComponent extends BaseMapListDirective {
  asList = true;
}

@Component({
  selector: 'app-fields-map',
  templateUrl: './map-list.template.html',
  styleUrls: ['./map.component.scss']
})
export class FieldMapComponent extends BaseMapListDirective {
  asList = false;
}
