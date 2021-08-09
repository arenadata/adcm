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
import { Component, forwardRef, OnInit } from '@angular/core';

import { BaseFormDirective } from '../../../shared/add-component/base-form.directive';
import { ADD_SERVICE_PROVIDER } from '../../../shared/add-component/add-service-token';
import { ConfigGroupAddService } from '../../service/config-group-add.service';

@Component({
  selector: 'app-config-group-add',
  template: `
    <ng-container [formGroup]="form">
      <app-input [form]="form" [label]="'Name'" [controlName]="'name'" [isRequired]="true"></app-input>
      <app-input [form]="form" [label]="'Description'" [controlName]="'description'"></app-input>
      <app-add-controls [disabled]="!form.valid" (cancel)="onCancel()" (save)="save()"></app-add-controls>
    </ng-container>
  `,
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => ConfigGroupAddService) }
  ],
})
export class AddConfigGroupComponent extends BaseFormDirective implements OnInit {

  ngOnInit(): void {
    this.form = this.service.model().form;
  }

  save(): void {
    // const data = clearEmptyField(this.form.value) as ConfigGroup;
    //
    // this.service
    //   .addConfigGroup(data)
    //   .pipe(take(1))
    //   .subscribe((_) => this.onCancel());
  }
}
