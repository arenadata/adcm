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

import { ConfigOptions, ConfigResultTypes, ConfigValueTypes, FieldOptions, FieldStack, IConfig, PanelOptions, ValidatorInfo, controlType } from './types';
import { matchType } from './yspec/yspec.service';

export interface IToolsEvent {
  name: string;
  conditions?: { advanced: boolean; search: string } | boolean;
}

@Injectable()
export class FieldService {
  constructor(private fb: FormBuilder) {}

  isVisibleField = (a: ConfigOptions) => !a.ui_options || !a.ui_options.invisible;
  isInvisibleField = (a: ConfigOptions) => a.ui_options && a.ui_options.invisible;
  isAdvancedField = (a: ConfigOptions) => a.ui_options && a.ui_options.advanced && !a.ui_options.invisible;
  isHidden = (a: FieldStack) => a.ui_options && (a.ui_options.invisible || a.ui_options.advanced);

  getPanels(data: IConfig): (FieldOptions | PanelOptions)[] {
    if (data && data.config) {
      const fo = data.config.filter(a => a.type !== 'group' && a.subname);
      return data.config
        .filter(a => a.name !== '__main_info')
        .reduce((p, c) => {
          if (c.subname) return p;
          if (c.type !== 'group') return [...p, this.checkYspec(this.getFieldBy(c))];
          else return [...p, this.fillDataOptions(c, fo)];
        }, []);
    }
    return [];
  }

  fillDataOptions(a: FieldStack, fo: FieldStack[]) {
    return {
      ...a,
      hidden: this.isHidden(a),
      options: fo
        .filter(b => b.name === a.name)
        .map(b => this.getFieldBy(b))
        .map(c => {
          c.name = c.subname;
          return c;
        })
        .map(b => this.checkYspec(b))
    };
  }

  checkYspec(a: FieldOptions): FieldOptions | PanelOptions {
    if (a.limits?.yspec) {
      const b = (<unknown>a) as PanelOptions;
      b.options = [];
      return b;
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

  setValidator(field: { validator: ValidatorInfo; controlType: controlType }) {
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
    return this.fb.group(options.reduce((p, c) => this.runByTree(c, p), {}));
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
    controls[name] = this.fb.control(field.type === 'option' ? { value: field.value, disabled: field.disabled } : field.value, this.setValidator(field));
    if (field.controlType === 'password') {
      if (!field.ui_options || (field.ui_options && !field.ui_options.no_confirm)) {
        controls[`confirm_${name}`] = this.fb.control(field.value, this.setValidator(field));
      }
    }
    return controls;
  }

  filterApply(dataOptions: (FieldOptions | PanelOptions)[], c: { advanced: boolean; search: string }): (FieldOptions | PanelOptions)[] {
    return dataOptions.filter(a => this.isVisibleField(a)).map(a => this.handleTree(a, c));
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
  parseValue(form: FormGroup, raw: FieldStack[]): { [key: string]: string | number | boolean | object | [] } {
    const __main_info = this.findField(raw, '__main_info');
    const value = __main_info && __main_info.required ? { ...form.value, __main_info: __main_info.value } : { ...form.value };
    return this.runParse(raw, value);
  }

  runParse(raw: FieldStack[], value: { [key: string]: any }, parentName?: string): { [key: string]: ConfigResultTypes } {
    const excluteTypes = ['json', 'map', 'list'];
    return Object.keys(value).reduce((p, c) => {
      const data = value[c];
      const field = this.findField(raw, c, parentName);

      if (field && !field.read_only) {
        if (field.type === 'structure') p[c] = this.runYspecParse(data, field);
        else if (isObject(data) && !excluteTypes.includes(field.type)) {
          const br = this.runParse(raw, data, field.name);
          if (Object.keys(br).length) p[c] = br;
        } else if (field) p[c] = this.checkValue(data, field.type);
      }
      return p;
    }, {});
  }

  findField(raw: FieldStack[], name: string, parentName?: string): FieldStack {
    return raw.find(a => (parentName ? a.name === parentName && a.subname === name : a.name === name));
  }

  runYspecParse(value: any, field: FieldStack) {
    return this.runYspec(value, field.limits.rules);
  }

  runYspec(value: any, rules: any) {
    switch (rules.type) {
      case 'list': {
        return value.filter(a => !!a).map(a => this.runYspec(a, rules.options));
      }
      case 'dict': {
        return Object.keys(value).reduce((p, c) => {
          const v = this.runYspec(
            value[c],
            rules.options.find(b => b.name === c)
          );
          return v !== null ? { ...p, [c]: v } : { ...p };
        }, {});
      }
      default: {
        return this.checkValue(value, rules.type);
      }
    }
  }

  checkValue(value: ConfigResultTypes, type: ConfigValueTypes) {
    if (value === '' || value === null) return null;

    switch (type) {
      case 'map':
        return typeof value === 'object'
          ? Object.keys(value)
              .filter(a => !!a)
              .reduce((p, c) => ({ ...p, [c]: value[c] }), {})
          : new TypeError('FieldService::checkValue - value is not Object');

      case 'list':
        return Array.isArray(value) ? (value as Array<string>).filter(a => !!a) : new TypeError('FieldService::checkValue - value is not Array');
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
