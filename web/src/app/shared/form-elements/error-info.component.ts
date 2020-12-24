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
import { Component, Input } from '@angular/core';
import { FormControl } from '@angular/forms';

import { IFieldOptions } from '../configuration/types';

@Component({
  selector: 'app-error-info',
  template: `
    <mat-error *ngIf="hasError('required')">Field [{{ field.display_name }}] is required!</mat-error>
    <mat-error *ngIf="hasError('pattern')">Field [{{ field.display_name }}] is invalid!</mat-error>
    <mat-error *ngIf="hasError('min')">Field [{{ field.display_name }}] value cannot be less than {{ field.validator.min }}!</mat-error>
    <mat-error *ngIf="hasError('max')">Field [{{ field.display_name }}] value cannot be greater than {{ field.validator.max }}!</mat-error>
    <mat-error *ngIf="hasError('jsonParseError')">Json parsing error!</mat-error>
  `
})
export class ErrorInfoComponent {
  @Input() control: FormControl;
  @Input() field: IFieldOptions;

  hasError(name: string) {
    return this.control.hasError(name);
  }
}
