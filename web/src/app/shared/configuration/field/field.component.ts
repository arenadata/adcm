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
import { Component, HostBinding, InjectionToken, Input, OnChanges, OnInit, SimpleChanges, ViewChild } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { FieldDirective } from '@app/shared/form-elements/field.directive';
import { BaseMapListDirective } from '@app/shared/form-elements/map.component';

import { SchemeComponent } from '../scheme/scheme.component';
import { IFieldOptions } from '../types';
import { BaseDirective } from '@app/adwp';
import { PasswordComponent } from "@app/shared/form-elements/password/password.component";
import { SecretTextComponent } from "@app/shared/form-elements/secret-text/secret-text.component";
import { SecretFileComponent } from "@app/shared/form-elements/secret-file/secret-file.component";

export const CONFIG_FIELD = new InjectionToken('Config field');

@Component({
  selector: 'app-field',
  templateUrl: './field.component.html',
  styleUrls: ['./field.component.scss'],
  providers: [
    { provide: CONFIG_FIELD, useExisting: FieldComponent }
  ]
})
export class FieldComponent extends BaseDirective implements OnInit, OnChanges {
  @Input()
  options: IFieldOptions;

  @HostBinding('class.read-only') get readOnly() {
    return this.options.read_only;
  }
  @HostBinding('class') hostClass = 'field-row w100 d-flex';

  @Input()
  form: FormGroup;
  currentFormGroup: FormGroup;

  noRefreshButtonFields = ['password', 'secrettext', 'secretmap', 'secretfile'];
  disabled: boolean = false;

  @ViewChild('cc') inputControl: FieldDirective;
  @ViewChild('pass') passControl: FieldDirective;
  @ViewChild('sc') secretTextControl: FieldDirective;
  @ViewChild('sf') secretFileControl:  FieldDirective

  ngOnInit() {
    this.initCurrentGroup();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!changes.form.firstChange) this.initCurrentGroup();
  }

  isSecretField(): boolean {
    return this.noRefreshButtonFields.includes(this.options.controlType);
  }

  initCurrentGroup() {
    const [_, name] = this.options.key.split('/');
    this.currentFormGroup = name ? (this.form.controls[name] as FormGroup) : this.form;
  }

  getTestName() {
    return `${this.options.name}${this.options.subname ? '/' + this.options.subname : ''}`;
  }

  outputValue(v: string, isPart = false) {
    if (this.options.type === 'password') v = v.replace(/\w/gi, '*');
    if (['secrettext', 'secretfile'].includes(this.options.type)) v = '****';

    return v.length > 80 ? (isPart ? v : `${v.substr(0, 80)}...`) : v;
  }

  isAdvanced() {
    return this.options.ui_options && this.options.ui_options.advanced;
  }

  /**
   * TODO: should be own restore() for each fieldComponent   *
   * @member FieldComponent
   */
  restore() {
    if (this.disabled) return;

    const field = this.currentFormGroup.controls[this.options.name];
    const defaultValue = this.options.default;
    const type = this.options.type;
    
    if (field) {
      if (type === 'json') {
        field.setValue(defaultValue === null ? '' : JSON.stringify(defaultValue, undefined, 4));
      } else if (type === 'boolean') {
        const allow = String(defaultValue) === 'true' || String(defaultValue) === 'false' || String(defaultValue) === 'null';
        field.setValue(allow ? defaultValue : null);
      } else if (type === 'password') {
        field.setValue(defaultValue);
        field.updateValueAndValidity();

        const confirm = this.currentFormGroup.controls[`confirm_${this.options.name}`];
        if (confirm) {
          confirm.setValue(defaultValue);
          confirm.updateValueAndValidity();
        }
      } else if (type === 'map' || type === 'list') {
        this.options.value = defaultValue;
        (this.inputControl as BaseMapListDirective).reload();
      } else if (type === 'structure') {
        this.options.value = defaultValue;
        (this.inputControl as SchemeComponent).reload();
      } else field.setValue(defaultValue);

      this.options.value = field.value;
      this.form.updateValueAndValidity();
    }
  }

  reset() {
    const type = this.options.type;

    if (this.disabled) return;
    if (!this.noRefreshButtonFields.includes(type)) return;

    const field = this.currentFormGroup.controls[this.options.name];

    switch (type) {
      case('password'):
        field.setValue(null);
        field.updateValueAndValidity();

        const confirm = this.currentFormGroup.controls[`confirm_${this.options.name}`];
        if (confirm) {
          confirm.setValue(null);
          confirm.updateValueAndValidity();
        }
        (this.passControl as PasswordComponent).isHideDummy = true;
        this.passControl['dummy'] = '';
        break;
      case('secretfile'):
        field.setValue(null);
        field.updateValueAndValidity();
        (this.secretFileControl as SecretFileComponent).clear();
        break;
      case('secrettext'):
        field.setValue(null);
        field.updateValueAndValidity();
        (this.secretTextControl as SecretTextComponent).clear();
        break;
      case('secretmap'):
        field.setValue(null);
        field.updateValueAndValidity();
        break;
    }

    this.options.value = field.value;
    this.form.updateValueAndValidity();
  }
}
