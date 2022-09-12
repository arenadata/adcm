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
import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { AbstractControl, FormGroup } from '@angular/forms';
import { MatExpansionPanel } from '@angular/material/expansion';
import { MatSlideToggleChange } from '@angular/material/slide-toggle';
import { FieldService } from '@app/shared/configuration/services/field.service';
import { IFieldOptions, IPanelOptions } from '../types';
import { AttributeService } from "@app/shared/configuration/attributes/attribute.service";

@Component({
  selector: 'app-group-fields',
  templateUrl: './group-fields.component.html',
  styles: [
    '.title {font-size: 22px;}',
    '.title > mat-slide-toggle {margin-left: 20px;}',
    '.advanced {border: dotted 1px #00e676;}',
    'mat-panel-description {justify-content: flex-end;}',
    'mat-checkbox {margin-right: 10px;}',
  ],
})
export class GroupFieldsComponent implements OnInit {
  active = true;
  group_config: { [key: string]: boolean };
  @Input() panel: IPanelOptions;
  @Input() form: FormGroup;
  @Input() uniqId: string;
  @ViewChild('ep') expanel: MatExpansionPanel;

  constructor(private service: FieldService, private attributesSrv: AttributeService) {}

  ngOnInit(): void {
    if (this.panel.activatable) this.activatable(this.panel.active);
    this.group_config = this.panel?.group_config;
  }

  get isAdvanced() {
    return this.panel.ui_options && this.panel.ui_options.advanced;
  }

  activeToggle(e: MatSlideToggleChange): void {
    this.panel.active = e.checked;
    this.activatable(e.checked);
  }

  activatable(flag: boolean): void {
    this.active = flag;
    this.checkFields(this.active);
  }

  checkFields(flag: boolean): void {
    this.panel.options
      .filter((a) => !('options' in a))
      .forEach((a: IFieldOptions) => {
        const split = a.key.split('/');
        const [name, ...other] = split;
        const currentFormGroup = (<unknown>other.reverse().reduce((p, c) => p.get(c), this.form)) as FormGroup;
        const formControl = currentFormGroup.controls[name];
        this.updateValidator(formControl, flag, a);
        if (a.type === 'password') this.updateValidator(currentFormGroup.controls['confirm_' + name], flag, a, formControl);
      });
  }

  updateValidator(formControl: AbstractControl, flag: boolean, a: IFieldOptions, currentFormControl?: AbstractControl): void {
    if (formControl) {
      if (!flag) formControl.clearValidators();
      else formControl.setValidators(this.service.setValidator(a, currentFormControl));
      formControl.updateValueAndValidity();
      formControl.markAsTouched();
      this.form.updateValueAndValidity();
    }
  }

  groupCheckboxExist() {
    return this.panel?.type==='group' && this.panel.activatable && this.panel?.group_config?.exist;
  }

  clickGroupCheckbox(event): void {
    this.attributesSrv.groupCheckboxToggle(this.panel.name, !this.group_config.checkboxValue, this.uniqId);
    this.panel.value = this.group_config.checkboxValue = !this.group_config.checkboxValue;
    event.preventDefault();
    event.stopPropagation();
  }
}
