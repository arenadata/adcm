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
import { Component, Input, OnInit, QueryList, ViewChild, ViewChildren } from '@angular/core';
import { AbstractControl, FormGroup } from '@angular/forms';
import { MatExpansionPanel } from '@angular/material/expansion';
import { MatSlideToggleChange } from '@angular/material/slide-toggle';

import { FieldService } from '../field.service';
import { FieldComponent } from '../field/field.component';
import { FieldOptions, PanelOptions, IConfig, IConfigAttr } from '../types';

@Component({
  selector: 'app-group-fields',
  templateUrl: './group-fields.component.html',
  styleUrls: ['./group-fields.component.scss'],
})
export class GroupFieldsComponent implements OnInit {
  @Input() panel: PanelOptions;
  @Input() form: FormGroup;
  @Input() rawConfig: IConfig;
  @ViewChild('ep') expanel: MatExpansionPanel;

  checked = true;
  attrConfig: IConfigAttr = {};

  @ViewChildren(FieldComponent)
  fields: QueryList<FieldComponent>;

  constructor(private service: FieldService) {}

  ngOnInit(): void {
    this.attrConfig = this.rawConfig.attr || {};
    if (this.attrConfig[this.panel.name]) {
      this.checked = this.attrConfig[this.panel.name].active;
      this.checkFields(this.checked);
    }
  }

  isPanel(item: FieldOptions | PanelOptions) {
    return 'options' in item && !item.hidden;
  }

  getForm() {
    return this.form.controls[this.panel.name];
  }

  isAdvanced() {
    return this.panel.ui_options && this.panel.ui_options.advanced;
  }

  activeToggle(e: MatSlideToggleChange) {
    this.attrConfig[this.panel.name].active = e.checked;
    this.checked = e.checked;
    this.checkFields(e.checked);
  }

  checkFields(flag: boolean) {
    this.panel.options
      .filter((a) => !('options' in a))
      .forEach((a: FieldOptions) => {
        const split = a.key.split('/');

        const [name, ...other] = split;
        const currentFormGroup = other.reverse().reduce((p, c) => p.get(c), this.form) as FormGroup;
        const formControl = currentFormGroup.controls[name];

        this.updateValidator(formControl, a, flag);
        if (a.type === 'password') this.updateValidator(currentFormGroup.controls['confirm_' + name], a, flag);
      });
  }

  updateValidator(formControl: AbstractControl, a: FieldOptions, flag: boolean) {
    if (formControl) {
      if (!flag) {
        formControl.clearValidators();
      } else if (a.validator) {
        formControl.setValidators(this.service.setValidator(a));
      }
      if (this.checkForm()) {
        this.form.setErrors({ error: 'There are not visible fields in this form' });
      } else {
        formControl.updateValueAndValidity();
        this.form.updateValueAndValidity();
      }
    }
  }

  checkForm() {
    return  this.rawConfig.config
    .filter((a) => a.type !== 'group')
    .filter((a) => !a.read_only)
    .filter((a) => !(a.ui_options && a.ui_options.invisible)).length === 0;
  }

  trackBy(index: number, item: FieldOptions): string {
    return item.key;
  }
}
