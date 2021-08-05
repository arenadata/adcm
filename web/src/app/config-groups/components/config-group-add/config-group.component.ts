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

import { BaseFormDirective } from '../../../shared/add-component/base-form.directive';
import { clearEmptyField } from '../../../core/types';
import { take } from 'rxjs/operators';
import { ConfigGroup } from '../../model/config-group.model';

@Component({
  selector: 'app-config-group-add',
  template: `
    <ng-container [formGroup]="form">
      <app-input [form]="form" [label]="'Name'" [controlName]="'name'" [isRequired]="true"></app-input>
      <app-input [form]="form" [label]="'Description'" [controlName]="'description'"></app-input>
      <app-add-controls [disabled]="!form.valid" (cancel)="onCancel()" (save)="save()"></app-add-controls>
    </ng-container>
  `,
})
export class AddConfigGroupComponent extends BaseFormDirective implements OnInit {

  ngOnInit(): void {
    this.form = this.service.model('configgroup').form;
  }

  save(): void {
    const data = clearEmptyField(this.form.value) as ConfigGroup;

    this.service
      .addConfigGroup(data)
      .pipe(take(1))
      .subscribe((_) => this.onCancel());
  }
}
