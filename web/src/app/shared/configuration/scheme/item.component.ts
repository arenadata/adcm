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
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { IYField, reqursionType } from '../yspec/yspec.service';
import { IValue } from './root.component';

@Component({
  selector: 'app-item-scheme',
  template: `
    <ng-container [formGroup]="form">
      <ng-container *ngIf="item.parent === 'list'; else other">
        <mat-form-field *ngIf="item.rules.controlType === 'textbox'">
          <input matInput [formControlName]="index" [value]="item.value" />
          <button *ngIf="item.parent === 'list'" mat-icon-button matSuffix color="primary" (click)="emmit()">
            <mat-icon>highlight_off</mat-icon>
          </button>
        </mat-form-field>
      </ng-container>

      <ng-template #other>
        <div class="chbox-field" *ngIf="item.rules.controlType === 'boolean'">
          <mat-checkbox [formControlName]="item.name" [checked]="item.value">{{ item.name }}</mat-checkbox>
        </div>
        <mat-form-field *ngIf="item.rules.controlType === 'textbox'">
          <mat-label>{{ item.name }}</mat-label>
          <input matInput [formControlName]="item.name" />
        </mat-form-field>
      </ng-template>
    </ng-container>
  `,
  styles: ['mat-form-field {margin: 6px 0 0; width: 100%}', '.chbox-field {margin:6px 0;}']
})
export class ItemComponent {
  @Input() item: { rules: IYField; name: string; value: IValue; parent: reqursionType };
  @Input() index: number;
  @Input() form: FormGroup;
  @Output() remove = new EventEmitter<number>();
  emmit() {
    this.remove.emit(this.index);
  }
}
