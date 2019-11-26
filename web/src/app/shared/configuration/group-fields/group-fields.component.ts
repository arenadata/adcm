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
import { IConfig, FieldOptions } from '@app/core/types';

import { FieldService, PanelInfo } from '../field.service';
import { FieldComponent } from '../field/field.component';

@Component({
  selector: 'app-group-fields',
  templateUrl: './group-fields.component.html',
  styleUrls: ['./group-fields.component.scss'],
})
export class GroupFieldsComponent implements OnInit {
  @Input() panel: PanelInfo;
  @Input() form: FormGroup;
  @Input() globalConfig: IConfig;
  @ViewChild('ep', { static: false }) expanel: MatExpansionPanel;
  checked = true;

  @ViewChildren(FieldComponent)
  fields: QueryList<FieldComponent>;

  constructor(private service: FieldService) {}

  ngOnInit(): void {
    if (this.globalConfig.attr && this.globalConfig.attr[this.panel.name]) {
      this.checked = this.globalConfig.attr[this.panel.name].active;
      // this.globalConfig.config.filter(a => a.name === this.panel.name).forEach(a => (a.read_only = !this.checked));
      this.checkFields(this.checked);
    }
  }

  isAdvanced() {
    return this.panel.ui_options && this.panel.ui_options.advanced;
  }

  activeToggle(e: MatSlideToggleChange) {
    this.globalConfig.attr[this.panel.name].active = e.checked;
    this.checked = e.checked;
    this.checkFields(e.checked);
  }

  checkFields(flag: boolean) {
    this.panel.options.forEach(a => {
      const name = `${a.subname ? a.subname + '/' : ''}${this.panel.name}`;
      const formControl = this.form.controls[name];
      this.updateValidator(formControl, a, flag);
      if (a.type === 'password') {
        this.updateValidator(this.form.controls['confirm_' + name], a, flag);
      }
    });
  }

  updateValidator(formControl: AbstractControl, a: FieldOptions, flag: boolean) {
    if (formControl) {
      if (!flag) {
        formControl.clearValidators();
      } else if (a.validator) {
        formControl.setValidators(this.service.setValidator(a));
      }
      formControl.updateValueAndValidity();
      this.form.updateValueAndValidity();
    }
  }
}
