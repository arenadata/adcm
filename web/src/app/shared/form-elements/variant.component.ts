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
import { Component, OnInit } from '@angular/core';

import { FieldDirective } from './field.directive';

@Component({
  selector: 'app-fields-variant',
  template: `
    <ng-container [formGroup]="form">
      <mat-form-field>
        <ng-container *ngIf="field.limits?.source?.strict; else ac">
          <mat-select [(value)]="field.value" [formControlName]="field.name">
            <mat-option *ngFor="let option of field.limits?.source?.value || []" [value]="option">{{ option }}</mat-option>
          </mat-select>
        </ng-container>
        <ng-template #ac>
          <input type="text" matInput [formControlName]="field.name" [matAutocomplete]="auto" />
          <mat-autocomplete #auto="matAutocomplete">
            <mat-option *ngFor="let option of field.limits?.source?.value || []" [value]="option">
              {{ option }}
            </mat-option>
          </mat-autocomplete>
        </ng-template>
        <mat-error *ngIf="!isValid"><app-error-info [field]="field" [control]="control"></app-error-info></mat-error>
      </mat-form-field>
    </ng-container>
  `,
})
export class VariantComponent extends FieldDirective implements OnInit {
  ngOnInit() {
    if (this.field.read_only) {
      this.control.disable();
    }
  }
}
