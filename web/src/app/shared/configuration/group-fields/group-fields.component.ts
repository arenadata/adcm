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
import { FieldService } from '@app/shared/configuration/field.service';

import { IFieldOptions, IPanelOptions } from '../types';

@Component({
  selector: 'app-group-fields',
  templateUrl: './group-fields.component.html',
  styles: [
    '.title {font-size: 22px;}',
    '.title > mat-slide-toggle {margin-left: 20px;}',
    '.advanced {border: dotted 1px #00e676;}',
    'mat-panel-description {justify-content: flex-end;}',
  ],
})
export class GroupFieldsComponent implements OnInit {
  active = true;
  @Input() panel: IPanelOptions;
  @Input() form: FormGroup;
  @ViewChild('ep') expanel: MatExpansionPanel;

  constructor(private service: FieldService) {}

  ngOnInit(): void {
    if (this.panel.activatable) this.activatable(this.panel.active);
  }

  get isAdvanced() {
    return this.panel.ui_options && this.panel.ui_options.advanced;
  }

  activeToggle(e: MatSlideToggleChange) {
    this.panel.active = e.checked;
    this.activatable(e.checked);
  }

  activatable(flag: boolean) {
    this.active = flag;
    this.checkFields(this.active);
  }

  checkFields(flag: boolean) {
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

  updateValidator(formControl: AbstractControl, flag: boolean, a: IFieldOptions, currentFormControl?: AbstractControl) {
    if (formControl) {
      if (!flag) formControl.clearValidators();
      else formControl.setValidators(this.service.setValidator(a, currentFormControl));
      formControl.updateValueAndValidity();
      formControl.markAsTouched();
      this.form.updateValueAndValidity();
    }
  }
}
