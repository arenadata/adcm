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
import { AfterViewInit, Component, OnInit } from '@angular/core';
import { Observable, of } from 'rxjs';

import { FieldDirective } from './field.directive';

@Component({
  selector: 'app-fields-dropdown',
  template: `
    <ng-container [formGroup]="form">
      <mat-form-field>
        <ng-container *ngIf="field.read_only; else dd">
          <input matInput [formControlName]="field.name" [readonly]="true" [value]="field.value" />
        </ng-container>
        <ng-template #dd>
          <mat-select [(value)]="field.value" [formControlName]="field.name">
            <mat-option *ngFor="let option of options$ | async" [value]="option.id">{{ option.name }}</mat-option>
          </mat-select>
        </ng-template>
      </mat-form-field>
    </ng-container>
  `,
})
export class DropdownComponent extends FieldDirective implements OnInit, AfterViewInit {
  options$: Observable<{ id: number | string; name: string }[]>;

  ngAfterViewInit() {
    setTimeout(() => {
      this.form.get(this.field.name).markAsTouched();
    }, 100)
  }

  ngOnInit() {
    super.ngOnInit();
    if (this.field.limits) {
      const o = Object.entries<string | number>(this.field.limits.option).map((e) => ({
        id: String(e[1]),
        name: e[0],
      }));
      this.options$ = of(o);
    }
  }
}
