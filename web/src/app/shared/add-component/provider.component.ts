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
import { Component, Input, OnInit, EventEmitter, Output, OnDestroy } from '@angular/core';
import { clearEmptyField, Provider } from '@app/core/types';

import { BaseFormDirective } from './base-form.directive';
import { Subscription } from 'rxjs';

export enum DisplayMode {
  default,
  inHost,
  noCluster
}

@Component({
  selector: 'app-add-provider',
  template: `
    <ng-container [formGroup]="form">
      <app-bundles [form]="form" [typeName]="'provider'"></app-bundles>
      <ng-container *ngIf="displayMode === 0; else asHost">
        <app-input [form]="form" [label]="'Hostprovider name'" [controlName]="'name'" [isRequired]="true"></app-input>
        <app-input [form]="form" [label]="'Description'" [controlName]="'description'"></app-input>
        <app-add-controls [disabled]="!form.valid" (cancel)="onCancel()" (save)="save()"></app-add-controls>
      </ng-container>
      <ng-template #asHost>
        <div class="row">
          <mat-form-field class="full-width">
            <input required matInput placeholder="Hostprovider name" formControlName="name" />
            <button [style.fontSize.px]="24" [disabled]="!form.valid" matTooltip="Create hostprovider" matSuffix mat-icon-button [color]="'accent'" (click)="save()">
              <mat-icon>add_box</mat-icon>
            </button>
            <mat-error *ngIf="form.get('name').hasError('required')">Hostprovider name is required </mat-error>
          </mat-form-field>
        </div>
      </ng-template>
    </ng-container>
  `,
  styles: ['.row {display: flex;}'],
})
export class ProviderComponent extends BaseFormDirective implements OnInit, OnDestroy {
  sgn: Subscription;
  @Input() displayMode: DisplayMode = DisplayMode.default;
  @Output() cancel = new EventEmitter();

  ngOnInit() {
    this.form = this.service.model('provider').form;
    this.sgn = this.service.genName(this.form);
  }

  ngOnDestroy() {
    this.sgn.unsubscribe();
  }

  save() {
    const data = clearEmptyField(this.form.value);
    this.service
      .add<Provider>(data, 'provider')
      .pipe(this.takeUntil())
      .subscribe((x) => {
        if (this.displayMode === 0) this.onCancel();
        else {
          this.form.reset();
          this.cancel.emit(x.id);
        }
      });
  }
}
