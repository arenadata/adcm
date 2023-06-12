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
import { Component, EventEmitter, HostListener, Input, OnInit, Output } from '@angular/core';
import { AbstractControl } from '@angular/forms';

import { controlType, IValidator } from '../types';
import { IYField } from '../yspec/yspec.service';
import { IControl } from './scheme.service';

@Component({
  selector: 'app-item-scheme',
  template: `
    <ng-container [formGroup]="item.form">
      <ng-container *ngIf="item.parent === 'list'; else other">
        <mat-form-field *ngIf="controlType === 'textbox'">
          <input matInput [formControlName]="index" [value]="item.value" />
          <button *ngIf="!isReadOnly && item.parent === 'list'" mat-icon-button matSuffix color="primary" (click)="emmit()">
            <mat-icon>highlight_off</mat-icon>
          </button>
        </mat-form-field>
      </ng-container>

      <ng-template #other>
        <div class="chbox-field" *ngIf="controlType === 'boolean'">
          <mat-checkbox [formControlName]="item.name">{{ item.name }}</mat-checkbox>
          <mat-error *ngIf="!isValid">
            <mat-error *ngIf="hasError('required')">Field [{{ item.name }}] is required!</mat-error>
          </mat-error>
        </div>
        <mat-form-field *ngIf="controlType === 'textbox'">
          <mat-label>{{ item.name }}</mat-label>
          <input matInput [formControlName]="item.name" [readonly]="isReadOnly" />
          <mat-error *ngIf="!isValid">
            <mat-error *ngIf="hasError('required')">Field [{{ item.name }}] is required!</mat-error>
            <mat-error *ngIf="hasError('pattern')">Field [{{ item.name }}] is invalid!</mat-error>
            <mat-error *ngIf="hasError('min')">Field [{{ item.name }}] value cannot be less than {{ validator.min }}!</mat-error>
            <mat-error *ngIf="hasError('max')">Field [{{ item.name }}] value cannot be greater than {{ validator.max }}!</mat-error>
          </mat-error>
        </mat-form-field>
      </ng-template>
    </ng-container>
  `,
  styles: [':host {flex: 1}', 'mat-form-field {margin: 6px 0 0; width: 100%}', '.chbox-field {margin:6px 0;}'],
})
export class ItemComponent implements OnInit {
  @Input() item: IControl;
  @Input() index: number;
  @Input() isReadOnly = false;
  @Output() remove = new EventEmitter<string>();

  @HostListener('keyup') changes() {
    this.control.markAsTouched();
  }

  controlType: controlType;
  validator: IValidator;

  ngOnInit() {
    const rules = this.item.rules as IYField;
    this.controlType = rules.controlType;
    this.validator = rules.validator;
    if (this.controlType === 'boolean' && this.isReadOnly) this.control.disable();
    this.item.form.markAllAsTouched();
  }

  emmit() {
    this.remove.emit(this.item.name);
  }

  get control() {
    return this.item.form.controls[this.item.name] as AbstractControl;
  }

  get isValid() {
    const f = this.control;
    return f.status !== 'INVALID' && (f.dirty || f.touched);
  }

  hasError(title: string) {
    return this.control.hasError(title);
  }
}
