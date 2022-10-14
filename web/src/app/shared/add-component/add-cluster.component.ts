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
import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { take } from 'rxjs/operators';

import { clearEmptyField, StackBase } from '@app/core/types';
import { BaseFormDirective } from './base-form.directive';
import { ICluster } from '@app/models/cluster';
import {Validators} from "@angular/forms";

@Component({
  selector: 'app-add-cluster',
  template: `
    <ng-container [formGroup]="form">
      <app-bundles [form]="form" [typeName]="'cluster'" (prototypeChanged)="prototypeChanged($event)"></app-bundles>
      <app-input [form]="form" [label]="'Cluster name'" [controlName]="'name'" [isRequired]="true"></app-input>
      <app-input [form]="form" [label]="'Description'" [controlName]="'description'"></app-input>
      <app-add-controls [disabled]="!form.valid" (cancel)="onCancel()" (save)="save()"></app-add-controls>
    </ng-container>
  `,
})
export class AddClusterComponent extends BaseFormDirective implements OnInit, OnDestroy {

  sgn: Subscription;
  private prototype: StackBase;

  ngOnInit() {
    this.form = this.service.model('cluster').form;
    this.form.controls['name'].setValidators([Validators.pattern(new RegExp(/^[a-z|A-Z]+(\w|\.|\-|\_|\s)*[a-z|A-Z|0-9]{1}$/))]);
    this.sgn = this.service.genName(this.form);
  }

  ngOnDestroy() {
    this.sgn.unsubscribe();
  }

  prototypeChanged(event: StackBase) {
    this.prototype = event;
  }

  save() {
    const data = clearEmptyField(this.form.value);
    this.service
      .add<ICluster>(data, 'cluster', this.prototype)
      .pipe(take(1))
      .subscribe((_) => this.onCancel());
  }

}
