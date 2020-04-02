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
import { Component, OnInit, ViewChild } from '@angular/core';
import { FormArray, FormGroup } from '@angular/forms';
import { FieldDirective } from '@app/shared/form-elements/field.directive';

import { IYContainer, IYField, YspecService } from '../yspec/yspec.service';
import { RootComponent } from './root.component';

@Component({
  selector: 'app-scheme',
  template: '<app-root-scheme #root [form]="itemFormGroup" [isReadOnly]="isReadOnly" [options]="rules" [value]="defaultValue"></app-root-scheme>'
})
export class SchemeComponent extends FieldDirective implements OnInit {
  itemFormGroup: FormGroup | FormArray;
  rules: IYField | IYContainer;
  defaultValue: any;
  isReadOnly = false;

  @ViewChild('root') rootComponent: RootComponent;

  constructor(private yspec: YspecService) {
    super();
  }

  ngOnInit() {
    this.isReadOnly = this.field.read_only;
    this.yspec.Root = this.field.limits.yspec;
    this.rules = this.yspec.build();
    this.field.limits.rules = this.rules;

    this.itemFormGroup = this.field.key
      .split('/')
      .reverse()
      .reduce((p: any, c: string) => p.get(c), this.form) as FormGroup;

    this.defaultValue = this.field.value || this.field.default;
    this.itemFormGroup = this.resetFormGroup(this.itemFormGroup.parent as FormGroup, this.rules.type === 'list');
    this.rules.name = '';
  }

  resetFormGroup(parent: FormGroup, isList: boolean) {
    const form = isList ? new FormArray([]) : new FormGroup({});
    parent.removeControl(this.field.name);
    parent.addControl(this.field.name, form);
    return form;
  }

  reload() {
    this.rootComponent.controls = [];
    this.itemFormGroup = this.resetFormGroup(this.itemFormGroup.parent as FormGroup, this.rules.type === 'list');
    this.rootComponent.form = this.itemFormGroup;
    setTimeout(_ => this.rootComponent.ngOnInit(), 1);
  }
}
