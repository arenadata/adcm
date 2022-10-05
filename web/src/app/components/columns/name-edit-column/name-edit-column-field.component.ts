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
import { Component, Input, OnInit } from '@angular/core';
import { BaseDirective } from '@adwp-ui/widgets';
import { FormControl } from "@angular/forms";
import { debounceTime } from "rxjs/operators";

@Component({
  selector: 'name-edit-column-field',
  template: `
    <ng-container>
      <form class="form">
        <mat-form-field class="full-width">
          <mat-label>Fully qualified domain name</mat-label>
          <input type="string" matInput [formControl]="form">
          <mat-error *ngIf="checkValidity()">Please enter a valid host name</mat-error>
        </mat-form-field>
      </form>
    </ng-container>
  `,
  styles: [`
    .form {
      min-width: 150px;
      max-width: 500px;
      width: 100%;
    }

    .full-width {
      width: 100%;
    }
  `]
})
export class NameEditColumnFieldComponent extends BaseDirective implements OnInit {
  @Input() model: any;

  row: any;
  form: FormControl;

  ngOnInit() {
    this.row = this.model.row;
    this.form = this.model.form;

    this.form.valueChanges
      .pipe(debounceTime(500))
      .subscribe(newValue => {
        this.form.markAsTouched();
        this.form.setValue(newValue, {emitEvent: false});
      });
  }

  checkValidity() {
    return this.form.invalid;
  }
}
