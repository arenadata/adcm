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
import { clearEmptyField, Cluster } from '@app/core/types';
import { filter } from 'rxjs/operators';

import { BaseFormDirective } from './base-form.directive';
import { GenName } from './naming';

@Component({
  selector: 'app-add-cluster',
  template: `
    <ng-container [formGroup]="form">
      <app-bundles [form]="form" [typeName]="'cluster'"></app-bundles>
      <app-input [form]="form" [label]="'Cluster name'" [controlName]="'name'" [isRequired]="true"></app-input>
      <app-input [form]="form" [label]="'Description'" [controlName]="'description'"></app-input>
      <app-add-controls [disabled]="!form.valid" (cancel)="onCancel()" (save)="save()"></app-add-controls>
    </ng-container>
  `
})
export class ClusterComponent extends BaseFormDirective implements OnInit {
  ngOnInit() {
    this.form = this.service.model('cluster').form;
    this.form
      .get('prototype_id')
      .valueChanges.pipe(
        filter(v => !!v),
        this.takeUntil()
      )
      .subscribe(() => {
        const field = this.form.get('name');
        if (!field.value) field.setValue(GenName.do());
      });
  }

  save() {
    const data = clearEmptyField(this.form.value);
    this.service
      .add<Cluster>(data, 'cluster')
      .pipe(this.takeUntil())
      .subscribe(_ => this.onCancel());
  }
}
