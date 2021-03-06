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
import { Component } from '@angular/core';

import { FieldDirective } from './field.directive';

@Component({
  selector: 'app-fields-textbox',
  template: `
    <ng-container [formGroup]="form">
      <mat-form-field>
        <input matInput [formControlName]="field.name" [readonly]="field.read_only" [type]="field.type" />
        <mat-error *ngIf="!isValid"><app-error-info [field]="field" [control]="control"></app-error-info></mat-error>
      </mat-form-field>
    </ng-container>
  `
})
export class TextBoxComponent extends FieldDirective {}
