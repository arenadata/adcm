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
import { AbstractControl, AbstractControlOptions, FormBuilder, FormGroup, ValidatorFn, Validators } from '@angular/forms';
import { isEmptyObject } from '@app/core/types';

import { ISearchParam } from '../main/main.service';
import {
  controlType,
  IConfig,
  IConfigAttr,
  IFieldOptions,
  IFieldStack,
  ILimits,
  IPanelOptions,
  IValidator,
  resultTypes,
  TNBase,
  TNForm
} from '../types';
import { AttributeService } from '@app/shared/configuration/attributes/attribute.service';

export type TFormOptions = IFieldOptions | IPanelOptions;

export interface IOutput {
  [key: string]: resultTypes;
}

export interface ISource {
  name: string;
  subname: string;
  type: TNForm;
  read_only: boolean;
  limits?: ILimits;
  value: any;
}

export interface IToolsEvent {
  name: string;
  conditions?: { advanced: boolean; search: string } | boolean;
}

const isVisibleField = (a: TFormOptions) => !a.ui_options?.invisible;
const isAdvancedField = (a: TFormOptions) => isVisibleField(a) && a.ui_options?.advanced;
const isHidden = (a: IFieldStack) => !!(a.ui_options?.invisible || a.ui_options?.advanced);

const typeToControl: Partial<{ [key in TNForm | controlType]: controlType }> = {
  bool: 'boolean',
  int: 'textbox',
  integer: 'textbox',
  float: 'textbox',
  string: 'textbox',
  file: 'textarea',
  text: 'textarea',
};

export const getControlType = (t: TNForm): controlType => typeToControl[t] || (t as controlType);

const intPattern = () => new RegExp(/^[-]?\d+$/);
const patternFn = {
  integer: intPattern,
  int: intPattern,
  float: () => new RegExp(/^[-]?[0-9]+(\.[0-9]+)?$/),
};

export const getPattern = (t: TNForm): RegExp => (patternFn[t] ? patternFn[t]() : null);

const fn = {
  boolean: (v: boolean | null, d: boolean | null, r: boolean): boolean | null => (String(v) === 'true' || String(v) === 'false' || String(v) === 'null' ? v : r ? d : null),
  json: (v: string): string => (v === null ? '' : JSON.stringify(v, undefined, 4)),
  map: (v: object, d: object): object => (!v ? d : v),
  list: (v: string[], d: string[]): string[] => (!v ? d : v),
  structure: (v: any): any => v,
};

export const getValue = (t: TNForm) => {
  const def = (value: number | string) => (value === null || value === undefined ? '' : String(value));
  return fn[t] ? fn[t] : def;
};

export const getKey = (name: string, subname: string): string => (subname ? `${subname}/${name}` : name);

export const getValidator = (required: boolean, min: number, max: number, type: TNForm) => ({
  required,
  min,
  max,
  pattern: getPattern(type),
});

const getField = (item: IFieldStack): IFieldOptions => {
  return {
    ...item,
    key: getKey(item.name, item.subname),
    value: getValue(item.type)(item.value, item.default, item.required),
    validator: getValidator(item.required, item.limits?.min, item.limits?.max, item.type),
    controlType: getControlType(item.type),
    hidden: item.name === '__main_info' || isHidden(item),
    compare: []
  };
};

const fo = (n: string) => (b: IFieldStack) => b.type !== 'group' && b.subname && b.name === n;
const isActive = (a: IConfigAttr, n: string) => a[n]?.active;
export const getOptions = (a: IFieldStack, d: IConfig) =>
  d.config
    .filter(fo(a.name))
    .map((f) => getField(f))
    // switch off validation for field if !(activatable: true && active: false) - line: 146
    .map((c) => ({ ...c, name: c.subname, activatable: a.activatable && !isActive(d.attr, a.name) }));

const getPanel = (a: IFieldStack, d: IConfig): IPanelOptions => ({
  ...a,
  hidden: isHidden(a),
  active: a.activatable ? isActive(d.attr, a.name) : true,
  options: getOptions(a, d),
});

const handleTree = (c: ISearchParam): ((a: TFormOptions) => TFormOptions) => (a: TFormOptions): TFormOptions => {
  if ('options' in a) {
    a.options = a.options.map(handleTree(c));
    if (c.search) a.hidden = a.options.filter((b) => !b.hidden).length === 0;
    else a.hidden = isAdvancedField(a) ? !c.advanced : false;
  } else if (isVisibleField(a)) {
    a.hidden = !(a.display_name.toLowerCase().includes(c.search.toLowerCase()) || String(a.value).toLocaleLowerCase().includes(c.search.toLocaleLowerCase()));
    if (!a.hidden && isAdvancedField(a)) a.hidden = !c.advanced;
  }
  return a;
};

const findAttrValue = <T extends object>(obj: T, key: string): boolean => {
  let value;
  for (let i in obj) {
    if (!obj.hasOwnProperty(i)) continue;
    if (typeof obj[i] === 'object') {
      value = findAttrValue<Object>(obj[i], key);
    } else if (i === key) {
      value = obj[i];
    }
  }
  return value;
};

@Injectable()
export class FieldService {
  attributesService: AttributeService | undefined;

  constructor(public fb: FormBuilder) {}

  /**
   * Parse and prepare source data from backend
   */
  public getPanels(data: IConfig): TFormOptions[] {
    return data?.config
      ?.filter((a) => a.name !== '__main_info')
      .reduce((p, c) => {
        if (c.subname) return p;
        if (c.type !== 'group') return [...p, getField(c)];
        else return [...p, getPanel(c, data)];
      }, []);
  }

  /**
   * Parse and prepare attrs data for group config from backend
   */
  public getAttrs(data: IConfig, groups: string[], dataOptions: TFormOptions[]): void {
    if (!data?.attr || !groups) return;

    groups.forEach((group) => {
      let disabled: boolean;
      const i = dataOptions.findIndex(item => item.name === group);
      const config = data.config.filter(c => c.name === group && c.type === 'group');

      if (config.length === 0) return;

      if (!data.attr?.custom_group_keys || !data.attr?.group_keys) {
        dataOptions[i].group_config = {
          'exist': false,
        }

        return;
      }

      if (config[0]?.read_only || !data.attr?.custom_group_keys[group].value) {
        disabled = true;
      } else if (data.attr?.custom_group_keys[group].value && data.attr?.group_keys[group].value) {
        disabled = false;
      }

      dataOptions[i] = {
        ...dataOptions[i],
        active: dataOptions[i]['active'],
        group_config: {
          'exist': true,
          'checkboxValue':  data.attr?.custom_group_keys[group].value && data.attr?.group_keys[group].value,
          'disabled': disabled
        }
      }
    })
  }

  /**
   * Generate FormGroup
   * @param options
   */
  public toFormGroup(options: TFormOptions[] = []): FormGroup {
    const check = (a: TFormOptions): boolean =>
      'options' in a
        ? a.activatable
          ? isVisibleField(a) // if group.activatable - only visible
          : isVisibleField(a) && !a.read_only // else visible an not read_only
            ? a.options.some((b) => check(b)) // check inner fields
            : false
        : isVisibleField(a) && !a.read_only; // for fields in group

    return this.fb.group(
      options.reduce((p, c) => this.runByTree(c, p), {}),
      {
        validator: () => (options.filter(check).length === 0 ? { error: 'Form is empty' } : null),
      } as AbstractControlOptions
    );
  }

  // TODO:
  private runByTree(field: TFormOptions, controls: { [key: string]: {} }): { [key: string]: {} } {
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

  private fillForm(field: IFieldOptions, controls: {}) {
    const name = field.subname || field.name;
    controls[name] = this.fb.control(field.value, field.activatable ? [] : this.setValidator(field));
    return controls;
  }

  /**
   * External use (scheme.service) to set validator for FormControl by type
   * @param field Partial<FieldOptions>{ ValidatorInfo, controlType }
   * @param controlToCompare
   */
  public setValidator(field: { validator: IValidator; controlType: controlType }, controlToCompare?: AbstractControl) {
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
  public filterApply(options: TFormOptions[], c: ISearchParam): TFormOptions[] {
    return options.filter((a) => isVisibleField(a)).map(handleTree(c));
  }

  /**
   * Output form, cast to source type
   */
  public parseValue(output: IOutput, source: ISource[]): IOutput {
    const findField = (name: string, p?: string): Partial<IFieldStack> => source.find((a) => (p ? a.name === p && a.subname === name : a.name === name));

    const runYspecParse = (v: any, f: Partial<IFieldOptions>) => ((!v || !Object.keys(v).length) && !f.value ? f.value : this.runYspec(v, f.limits.rules));

    const replaceEmptyObjectWithNull = (v: any): string => ((Array.isArray(v) && v?.length === 0) || JSON.stringify(v) === '{}' || this.emptyArrayInside(v)) ? null : v

    const runParse = (v: IOutput, parentName?: string): IOutput => {
      const runByValue = (p: IOutput, c: string) => {
        const checkType = (data: resultTypes | IOutput, field: Partial<IFieldStack>): resultTypes => {
          const { type } = field;
          if (type === 'structure') return replaceEmptyObjectWithNull(runYspecParse(data, field));
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

    return runParse(!!__main_info ? { ...output, __main_info: __main_info.value } : { ...output });
  }

  private runYspec(value: resultTypes, rules: any) {
    switch (rules?.type) {
      case 'list': {
        return (value as Array<TNBase>).filter((a) => !!a).map((a) => this.runYspec(a, rules.options));
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

  checkValue(value: resultTypes, type: TNForm): resultTypes {
    if (value === '' || value === null || isEmptyObject(value)) {
      if (type === 'map') return {};
      if (type === 'list') return [];
      return null;
    }

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

  emptyArrayInside(object: Object): boolean {
    if (object) {
      const keys = Object.keys(object);
      return keys?.length === 1 && Array.isArray(object[keys[0]]) && object[keys[0]]?.length === 0;
    }
  }
}
