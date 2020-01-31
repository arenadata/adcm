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
import { AbstractControl, FormBuilder, FormGroup, ValidatorFn, Validators } from '@angular/forms';
import { getControlType, getPattern, isObject } from '@app/core/types';

import { ConfigOptions, ConfigResultTypes, ConfigValueTypes, FieldOptions, FieldStack, IConfig, PanelOptions } from './types';
import { YspecStructure, matchType } from './YspecStructure';
import { YspecService } from './yspec/yspec.service';

export interface IToolsEvent {
  name: string;
  conditions?: { advanced: boolean; search: string } | boolean;
}

export type controlType = 'boolean' | 'textbox' | 'textarea' | 'json' | 'password' | 'list' | 'map' | 'dropdown';

@Injectable()
export class FieldService {
  globalConfig: IConfig;
  dataOptions: (FieldOptions | PanelOptions)[];
  formOptions: FieldOptions[];
  form = new FormGroup({});

  constructor(private fb: FormBuilder, private spec: YspecService) {}

  isVisibleField = (a: ConfigOptions) => !a.ui_options || !a.ui_options.invisible;
  isInvisibleField = (a: ConfigOptions) => a.ui_options && a.ui_options.invisible;
  isAdvancedField = (a: ConfigOptions) => a.ui_options && a.ui_options.advanced && !a.ui_options.invisible;
  isHidden = (a: FieldStack) => a.ui_options && (a.ui_options.invisible || a.ui_options.advanced);

  getPanels(data: IConfig): (FieldOptions | PanelOptions)[] {
    this.globalConfig = data;
    this.dataOptions = [];

    if (data && data.config.length) {
      this.formOptions = data.config.filter(a => a.type !== 'group').map((a: FieldStack) => this.getFieldBy(a));
      data.config.filter(a => a.name !== '__main_info').map(a => this.fillDataOptions(a));
    }
    return this.dataOptions;
  }

  fillDataOptions(a: FieldStack) {
    if (a.type === 'group') {
      this.dataOptions.push({
        ...a,
        hidden: this.isHidden(a),
        options: this.formOptions.filter(b => b.name === a.name).map(b => this.checkYspec(b))
      });
    } else if (!a.subname) this.dataOptions.push(this.checkYspec(this.getFieldBy(a)));
  }

  checkYspec(a: FieldOptions): FieldOptions | PanelOptions {
    a.name = a.subname || a.name;

    if (a.limits && a.limits.yspec) {

      this.spec.Root = a.limits.yspec;
      const output = this.spec.build();

      const yspec = new YspecStructure(a);
      return yspec.output;
    }
    return a;
  }

  getFieldBy(item: FieldStack): FieldOptions {
    const params: FieldOptions = {
      ...item,
      key: `${item.subname ? item.subname + '/' : ''}${item.name}`,
      disabled: item.read_only,
      value: this.getValue(item.type)(item.value, item.default, item.required),
      validator: {
        required: item.required,
        min: item.limits ? item.limits.min : null,
        max: item.limits ? item.limits.max : null,
        pattern: getPattern(item.type)
      },
      controlType: getControlType(item.type as matchType),
      hidden: item.name === '__main_info' || this.isHidden(item),
      compare: []
    };
    return params;
  }

  setValidator(field: FieldOptions) {
    const v: ValidatorFn[] = [];

    if (field.validator.required) v.push(Validators.required);
    if (field.validator.pattern) v.push(Validators.pattern(field.validator.pattern));
    if (field.validator.max !== undefined) v.push(Validators.max(field.validator.max));
    if (field.validator.min !== undefined) v.push(Validators.min(field.validator.min));

    if (field.controlType === 'json') {
      const jsonParse = (): ValidatorFn => {
        return (control: AbstractControl): { [key: string]: any } | null => {
          if (control.value) {
            try {
              JSON.parse(control.value);
              return null;
            } catch (e) {
              return { jsonParseError: { value: control.value } };
            }
          } else return null;
        };
      };
      v.push(jsonParse());
    }

    if (field.controlType === 'map') {
      const parseKey = (): ValidatorFn => {
        return (control: AbstractControl): { [key: string]: any } | null => {
          if (control.value && Object.keys(control.value).length && Object.keys(control.value).some(a => !a)) {
            return { parseKey: true };
          } else return null;
        };
      };
      v.push(parseKey());
    }

    return v;
  }

  toFormGroup(options: (FieldOptions | PanelOptions)[]): FormGroup {
    this.form = this.fb.group(options.reduce((p, c) => this.runByTree(c, p), {}));
    return this.form;
  }

  runByTree(field: FieldOptions | PanelOptions, controls: { [key: string]: {} }): { [key: string]: {} } {
    if ('options' in field) {
      controls[field.name] = this.fb.group(
        field.options.reduce((p, a) => {
          if ('options' in a) this.fb.group(this.runByTree(a, p));
          else this.fillForm(a, p);
          return p;
        }, {})
      );
      return controls;
    } else {
      return this.fillForm(field, controls);
    }
  }

  fillForm(field: FieldOptions, controls: {}) {
    const name = field.subname || field.name;
    controls[name] = this.fb.control({ value: field.value, disabled: field.disabled }, this.setValidator(field));
    if (field.controlType === 'password') {
      if (!field.ui_options || (field.ui_options && !field.ui_options.no_confirm)) {
        controls[`confirm_${name}`] = this.fb.control({ value: field.value, disabled: field.disabled }, this.setValidator(field));
      }
    }
    return controls;
  }

  filterApply(c: { advanced: boolean; search: string }): (FieldOptions | PanelOptions)[] {
    this.dataOptions.filter(a => this.isVisibleField(a)).map(a => this.handleTree(a, c));
    return [...this.dataOptions];
  }

  handleTree(a: FieldOptions | PanelOptions, c: { advanced: boolean; search: string }) {
    if ('options' in a) {
      const result = a.options.map(b => this.handleTree(b, c));
      if (c.search) a.hidden = a.options.filter(b => !b.hidden).length === 0;
      else a.hidden = this.isAdvancedField(a) ? !c.advanced : false;
      return result;
    } else if (this.isVisibleField(a)) {
      a.hidden = !(a.display_name.toLowerCase().includes(c.search.toLowerCase()) || JSON.stringify(a.value).includes(c.search));
      if (!a.hidden && this.isAdvancedField(a)) a.hidden = !c.advanced;
      return a;
    }
  }

  getValue(name: string) {
    const def = (value: number | string) => (value === null || value === undefined ? '' : String(value));

    const data = {
      boolean: (value: boolean | null, d: boolean | null, required: boolean) => {
        const allow = String(value) === 'true' || String(value) === 'false' || String(value) === 'null';
        return allow ? value : required ? d : null;
      },
      json: (value: string) => (value === null ? '' : JSON.stringify(value, undefined, 4)),
      map: (value: object, de: object) => (!value ? (!de ? {} : de) : value),
      list: (value: string[], de: string[]) => (!value ? (!de ? [] : de) : value),
      structure: (value: any) => value
    };

    return data[name] ? data[name] : def;
  }

  getFieldsBy(items: Array<FieldStack>): FieldOptions[] {
    return items.map(o => this.getFieldBy(o));
  }

  /**
   * Check the data
   *
   */
  parseValue(): { [key: string]: string | number | boolean | object | [] } {
    const __main_info = this.findField('__main_info');
    const value = __main_info && __main_info.required ? { ...this.form.value, __main_info: __main_info.value } : { ...this.form.value };
    return this.runParse(value);
  }

  runParse(value: { [key: string]: any }, parentName?: string): { [key: string]: ConfigResultTypes } {
    const excluteTypes = ['json', 'map', 'list'];
    return Object.keys(value).reduce((p, c) => {
      const data = value[c];
      const field = this.findField(c, parentName);
      if (field) {
        if (field.type === 'structure') p[c] = this.runYspecParse(data, field);
        else if (isObject(data) && !excluteTypes.includes(field.type)) p[c] = this.runParse(data, field.name);
        else if (field) p[c] = this.checkValue(data, field.type);
      }
      return p;
    }, {});
  }

  findField(name: string, parentName?: string): FieldStack {
    return this.globalConfig.config.find(a => (parentName ? a.name === parentName && a.subname === name : a.name === name));
  }

  runYspecParse(value: any, field: FieldStack) {
    const name = field.subname || field.name;
    const yo = this.dataOptions.find(a => a.name === field.name) as PanelOptions;
    const po = yo.options.find(a => a.name === field.subname) as PanelOptions;
    return this.runYspecByOptions(value, po);
  }

  runYspecByOptions(value: any, op: PanelOptions) {
    return Object.keys(value).reduce((p, c) => {
      const data = value[c];
      const key = op.options.find(a => a.name === c);
      if (isObject(data) && !Array.isArray(data)) p[c] = this.runYspecByOptions(data, key as PanelOptions);
      else if (key) p[c] = this.checkValue(data, key.type);
      return p;
    }, {});
  }

  checkValue(value: ConfigResultTypes, type: ConfigValueTypes) {
    if (value === '' || value === null) return null;

    switch (type) {
      case 'map':
        return Object.keys(value)
          .filter(a => a)
          .reduce((p, c) => {
            p[c] = value[c];
            return p;
          }, {});
      case 'list':
        return (value as Array<string>).filter(a => !!a);
    }

    if (typeof value === 'boolean') return value;

    if (typeof value === 'string')
      switch (type) {
        case 'option':
          if (!isNaN(+value)) return parseInt(value, 10);
          else return value;
        case 'integer':
        case 'int':
          return parseInt(value, 10);
        case 'float':
          return parseFloat(value);
        case 'json':
          return JSON.parse(value);
        default:
          return value;
      }
    return value;
  }
}
