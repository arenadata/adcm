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
import { Injectable } from '@angular/core';
import { AbstractControl, FormArray, FormControl, FormGroup, ValidatorFn } from '@angular/forms';
import { isObject } from '@app/core/types/func';

import { FieldService } from '../field.service';
import { IFieldOptions, TNForm, TNReq, TValue } from '../types';
import { IYContainer, IYField } from '../yspec/yspec.service';

export interface IValue {
  [key: string]: TValue;
}

export interface IControl {
  name: string;
  type: TNForm;
  rules: IYField | IYContainer | (IYField | IYContainer)[];
  form: FormGroup | FormArray;
  value: IValue | TValue;
  parent: TNReq;
}

@Injectable()
export class SchemeService {
  constructor(private service: FieldService) {}

  emptyValidator() {
    // const isEmptyArray = (v: any) => (Array.isArray(v) && v.length ? v.some((a) => isEmptyValue(a)) : false);
    // const isEmptyObj = (v: any) => (isObject(v) && Object.keys(v).length ? Object.keys(v).some((a) => isEmptyValue(v[a])) : false);
    const isEmptyValue = (v: any) => !v || (Array.isArray(v) && !v.length) || (isObject(v) && !Object.keys(v).length);
    return (): ValidatorFn => (control: AbstractControl): { [key: string]: any } | null => (isEmptyValue(control.value) ? { isEmpty: true } : null);
  }

  setCurrentForm(type: TNForm, parent: FormGroup, field: IFieldOptions) {
    const v = field.required ? this.emptyValidator()() : null;
    const current = type === 'list' || type === 'dict' ? (type === 'list' ? new FormArray([], v) : new FormGroup({}, v)) : new FormControl('', v);
    parent.setControl(field.name, current);
    return current;
  }

  addControlsDict(name: string, source: TValue | IValue, currentForm: FormArray, rules: IYContainer[]): IControl {
    const value = !source ? rules.reduce((p, c) => ({ ...p, [c.name]: '' }), {}) : source;

    const checkValue = () => {
      if (Array.isArray(rules)) {
        if (Array.isArray(value)) {
          return rules.some((a) => a.name === value[0]);
        } else if (typeof value === 'object') {
          return Object.keys(value).every((x) => rules.some((a) => a.name === x));
        }
      }
    };

    if (checkValue()) {
      const form = new FormGroup({});
      currentForm.push(form);
      return { name, value, type: 'dict', rules, form, parent: 'list' };
    }
  }

  addControls(name: string, value: TValue | IValue, currentForm: FormGroup | FormArray, opt: IYContainer | IYField | (IYContainer | IYField)[], type: TNReq): IControl {
    const rules = Array.isArray(opt) ? opt.find((a) => a.name === name) : opt;
    if (!rules) return;
    let form = currentForm;
    if (rules.type !== 'list' && rules.type !== 'dict') {
      const { validator, controlType } = rules as IYField;
      if (Array.isArray(currentForm.controls)) {
        name = currentForm.controls.length.toString();
        (currentForm as FormArray).push(new FormControl(value || '', this.service.setValidator({ validator, controlType })));
      } else (currentForm as FormGroup).addControl(rules.name, new FormControl(rules.type !== 'bool' ? value || '' : value, this.service.setValidator({ validator, controlType })));
    } else {
      form = rules.type === 'list' ? new FormArray([]) : new FormGroup({});
      (currentForm as FormGroup).addControl(rules.name, form);
    }

    return { name, value, type: rules.type, rules, form, parent: type };
  }
}
