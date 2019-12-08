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
import { clearEmptyField, Provider } from '@app/core/types';

import { BaseFormDirective } from './base-form.directive';

export enum DisplayMode {
  default,
  inHost,
}

@Component({
  selector: 'app-add-provider',
  template: `
    <ng-container [formGroup]="form">
      <app-bundles [form]="form" [typeName]="'provider'"></app-bundles>
      <ng-container *ngIf="displayMode === 0; else asHost">
        <app-input [form]="form" [label]="'Hostprovider name'" [controlName]="'name'" [isRequired]="true"></app-input>
        <app-input [form]="form" [label]="'Description'" [controlName]="'description'"></app-input>
        <p class="controls">
          <button mat-raised-button [disabled]="!form.valid" color="accent" (click)="save()">Save</button>
          <button mat-raised-button color="primary" (click)="onCancel()">Cancel</button>
        </p>
      </ng-container>
      <ng-template #asHost>
        <div class="row">
          <mat-form-field class="full-width">
            <input required matInput placeholder="Hostprovider name" formControlName="name" />
            <button
              [style.fontSize.px]="24"
              [disabled]="!form.valid"
              matTooltip="Create hostprovider"
              matSuffix
              mat-icon-button
              [color]="'accent'"
              (click)="save()"
            >
              <mat-icon>add_box</mat-icon>
            </button>
            <mat-error *ngIf="form.get('name').hasError('required')">Hostprovider name is required </mat-error>
          </mat-form-field>
        </div>
      </ng-template>
    </ng-container>
  `,
})
export class ProviderComponent extends BaseFormDirective implements OnInit {
  @Input() displayMode: DisplayMode = DisplayMode.default;

  ngOnInit() {
    this.form = this.service.model('provider').form;
  }

  save() {
    const data = clearEmptyField(this.form.value);
    this.service
      .add<Provider>(data, 'provider')
      .pipe(this.takeUntil())
      .subscribe(a => this.onCancel(a));
  }
}
