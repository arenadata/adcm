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
import { getControlType, getPattern, isEmptyObject } from '@app/core/types';

import { ConfigValueTypes, controlType, FieldOptions, FieldStack, IConfig, ILimits, PanelOptions, resultTypes, ValidatorInfo } from './types';
import { matchType, simpleType } from './yspec/yspec.service';

export type itemOptions = FieldOptions | PanelOptions;

export interface IOutput {
  [key: string]: resultTypes;
}

export interface ISource {
  name: string;
  subname: string;
  type: ConfigValueTypes;
  read_only: boolean;
  limits?: ILimits;
  value: any;
}

export interface IToolsEvent {
  name: string;
  conditions?: { advanced: boolean; search: string } | boolean;
}

@Injectable()
export class FieldService {
  constructor(public fb: FormBuilder) {}

  isVisibleField = (a: itemOptions) => !a.ui_options?.invisible;
  isAdvancedField = (a: itemOptions) => this.isVisibleField(a) && a.ui_options?.advanced;
  isHidden = (a: FieldStack) => !!(a.ui_options?.invisible || a.ui_options?.advanced);

  /**
   * Parse and prepare source data from backend
   */
  public getPanels(data: IConfig): itemOptions[] {
    const getValue = (type: string) => {
      const def = (value: number | string) => (value === null || value === undefined ? '' : String(value));

      const fn = {
        boolean: (value: boolean | null, d: boolean | null, required: boolean) => {
          const allow = String(value) === 'true' || String(value) === 'false' || String(value) === 'null';
          return allow ? value : required ? d : null;
        },
        json: (value: string) => (value === null ? '' : JSON.stringify(value, undefined, 4)),
        map: (value: object, de: object) => (!value ? de : value),
        list: (value: string[], de: string[]) => (!value ? de : value),
        structure: (value: any) => value,
      };

      return fn[type] ? fn[type] : def;
    };

    const getField = (item: FieldStack): FieldOptions => ({
      ...item,
      key: `${item.subname ? item.subname + '/' : ''}${item.name}`,
      value: getValue(item.type)(item.value, item.default, item.required),
      validator: {
        required: item.required,
        min: item.limits?.min,
        max: item.limits?.max,
        pattern: getPattern(item.type),
      },
      controlType: getControlType(item.type as matchType),
      hidden: item.name === '__main_info' || this.isHidden(item),
      compare: [],
    });

    const getPanels = (source: FieldStack, dataConfig: IConfig): PanelOptions => {
      const { config, attr } = dataConfig;
      const fo = (b: FieldStack) => b.type !== 'group' && b.subname && b.name === source.name;
      return {
        ...source,
        hidden: this.isHidden(source),
        active: source.activatable ? attr[source.name]?.active : true,
        options: config
          .filter(fo)
          .map(getField)
          // switch off validation for field if !(activatable: true && active: false) - line: 146
          .map((c) => ({ ...c, name: c.subname, activatable: source.activatable && !attr[source.name]?.active })),
      };
    };

    return data?.config
      ?.filter((a) => a.name !== '__main_info')
      .reduce((p, c) => {
        if (c.subname) return p;
        if (c.type !== 'group') return [...p, getField(c)];
        else return [...p, getPanels(c, data)];
      }, []);
  }

  /**
   * Generate FormGroup
   * @param options
   */
  public toFormGroup(options: itemOptions[] = []): FormGroup {
    const check = (a: itemOptions): boolean =>
      'options' in a
        ? a.activatable
          ? this.isVisibleField(a) // if group.activatable - only visible
          : this.isVisibleField(a) && !a.read_only // else visible an not read_only
          ? a.options.some((b) => check(b)) // check inner fields
          : false
        : this.isVisibleField(a) && !a.read_only; // for fields in group

    return this.fb.group(
      options.reduce((p, c) => this.runByTree(c, p), {}),
      {
        validator: () => (options.filter(check).length === 0 ? { error: 'Form is empty' } : null),
      }
    );
  }

  // TODO:
  private runByTree(field: itemOptions, controls: { [key: string]: {} }): { [key: string]: {} } {
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

  private fillForm(field: FieldOptions, controls: {}) {
    const name = field.subname || field.name;
    controls[name] = this.fb.control(field.value, field.activatable ? [] : this.setValidator(field));
    return controls;
  }

  /**
   * External use (scheme.service) to set validator for FormControl by type
   * @param field Partial<FieldOptions>{ ValidatorInfo, controlType }
   */
  public setValidator(field: { validator: ValidatorInfo; controlType: controlType }, controlToCompare?: AbstractControl) {
    const v: ValidatorFn[] = [];

    if (field.validator.required) v.push(Validators.required);
    if (field.validator.pattern) v.push(Validators.pattern(field.validator.pattern));
    //if (field.validator.max !== null)
    v.push(Validators.max(field.validator.max));
    //if (field.validator.min !== null)
    v.push(Validators.min(field.validator.min));

    if (field.controlType === 'password') {
      const passwordConfirm = (): ValidatorFn => (control: AbstractControl): { [key: string]: any } | null => {
        if (controlToCompare && controlToCompare.value !== control.value) return { notEqual: true };
        return null;
      };
      v.push(passwordConfirm());
    }

    if (field.controlType === 'json') {
      const jsonParse = (): ValidatorFn => (control: AbstractControl): { [key: string]: any } | null => {
        if (control.value) {
          try {
            JSON.parse(control.value);
            return null;
          } catch (e) {
            return { jsonParseError: { value: control.value } };
          }
        } else return null;
      };

      v.push(jsonParse());
    }

    if (field.controlType === 'map') {
      const parseKey = (): ValidatorFn => (control: AbstractControl): { [key: string]: any } | null =>
        control.value && Object.keys(control.value).length && Object.keys(control.value).some((a) => !a) ? { parseKey: true } : null;
      v.push(parseKey());
    }
    return v;
  }

  /**
   * Filter by group and all fields
   */
  public filterApply(dataOptions: itemOptions[], c: { advanced: boolean; search: string }): itemOptions[] {
    return dataOptions.filter((a) => this.isVisibleField(a)).map((a) => this.handleTree(a, c));
  }

  private handleTree(a: itemOptions, c: { advanced: boolean; search: string }) {
    if ('options' in a) {
      const result = a.options.map((b) => this.handleTree(b, c));
      if (c.search) a.hidden = a.options.filter((b) => !b.hidden).length === 0;
      else a.hidden = this.isAdvancedField(a) ? !c.advanced : false;
      return result;
    } else if (this.isVisibleField(a)) {
      a.hidden = !(a.display_name.toLowerCase().includes(c.search.toLowerCase()) || JSON.stringify(a.value).includes(c.search));
      if (!a.hidden && this.isAdvancedField(a)) a.hidden = !c.advanced;
      return a;
    }
  }

  /**
   * Output form, cast to source type
   */
  public parseValue(output: IOutput, source: ISource[]): IOutput {
    const findField = (name: string, p?: string): Partial<FieldStack> => source.find((a) => (p ? a.name === p && a.subname === name : a.name === name) && !a.read_only);

    const runYspecParse = (v: any, f: Partial<FieldOptions>) => ((v === {} || v === []) && !f.value ? f.value : this.runYspec(v, f.limits.rules));

    const runParse = (v: IOutput, parentName?: string): IOutput => {
      const runByValue = (p: IOutput, c: string) => {
        const checkType = (data: resultTypes | IOutput, field: Partial<FieldStack>): resultTypes => {
          const { type } = field;
          if (type === 'structure') return runYspecParse(data, field);
          else if (type === 'group') return this.checkValue(runParse(data as IOutput, field.name), type);
          else return this.checkValue(data, type);
        };

        const f = findField(c, parentName);
        if (f) {
          const result = checkType(v[c], f);
          return f.type !== 'group' || result ? { ...p, [c]: result } : p;
        }
        return p;
      };

      return Object.keys(v).reduce(runByValue, {});
    };

    const __main_info = findField('__main_info');
    return runParse(__main_info?.required ? { ...output, __main_info: __main_info.value } : { ...output });
  }

  private runYspec(value: resultTypes, rules: any) {
    switch (rules?.type) {
      case 'list': {
        return (value as Array<simpleType>).filter((a) => !!a).map((a) => this.runYspec(a, rules.options));
      }
      case 'dict': {
        return Object.keys(value).reduce((p, c) => {
          const r = rules.options.find((b: any) => b.name === c);
          const v = r ? this.runYspec(value[c], r) : null;
          return v !== null ? { ...p, [c]: v } : { ...p };
        }, {});
      }
      default: {
        return this.checkValue(value, rules?.type);
      }
    }
  }

  checkValue(value: resultTypes, type: ConfigValueTypes): resultTypes {
    if (value === '' || value === null || isEmptyObject(value)) return null;
    if (typeof value === 'boolean') return value;
    else if (typeof value === 'string')
      switch (type) {
        case 'option':
          return !isNaN(+value) ? parseInt(value, 10) : value;
        case 'integer':
        case 'int':
          return parseInt(value, 10);
        case 'float':
          return parseFloat(value);
        case 'json':
          return JSON.parse(value);
      }
    else
      switch (type) {
        case 'map':
          return Object.keys(value)
            .filter((a) => !!a)
            .reduce((p, c) => ({ ...p, [c]: value[c] }), {});

        case 'list':
          return Array.isArray(value) ? (value as Array<string>).filter((a) => !!a) : null;
      }

    return value;
  }
}
