import { IFieldOptions } from './../types';
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
import { getControlType, getKey, getOptions, getValidator, getValue, TFormOptions, IOutput } from '../field.service';

import { IConfig, IConfigAttr, IFieldStack, ILimits, IPanelOptions, IUIoptions, stateType, TNForm, TValue } from '../types';
import { IYContainer, IYField, IYspec } from '../yspec/yspec.service';

export class YContainer {}

export class YField {}

export class Yspec {
  constructor() {}
}

export class UIOptions implements IUIoptions {}

export class Limits {
  min: number;
  max: number;
  option: any;
  read_only: stateType[];
  active: boolean;
  rules: IYField | IYContainer;
  constructor(public yspec: IYspec) {}
  set Rules(rules: IYField | IYContainer) {
    this.rules = rules;
  }
}

export class FieldStack implements IFieldStack {
  subname: string;
  display_name: string;
  default: TValue = null;
  description?: string;
  limits: ILimits;
  ui_options: IUIoptions;

  constructor(
    id: number,
    public type: TNForm,
    public name: string = null,
    public value = null,
    public required = true,
    public read_only = false,
    public activatable = false
  ) {
    const dn = `field_${type}_${id}`;
    this.name = !this.name ? dn : this.name;
    this.subname = this.name === dn ? '' : `subname_${type}_${id}`;
    this.display_name = `display_${this.name}_${this.subname}`;
    this.value = getValue(this.type)(this.value, this.default, this.required);
  }

  set Limits(limits: ILimits) {
    this.limits = limits;
  }
  set UIOptions(options: IUIoptions) {
    this.ui_options = options;
  }
}

export class Configuration implements IConfig {
  id?: number;
  date?: string;
  description?: string;
  attr?: IConfigAttr;
  constructor(public config: IFieldStack[]) {}
}

export class FieldFactory {
  public static addGroup(id: number, params: TNForm[]): IFieldStack[] {
    const group = new FieldStack(id, 'group');
    return params.reduce((p, c, i) => [...p, new FieldStack(i, c, group.name)], [group]);
  }

  /**
   * return group if params as array
   */
  public static add(params: (TNForm | TNForm[])[]) {
    return params.reduce<IFieldStack[]>(
      (p, c, i) => [...p, ...(Array.isArray(c) ? this.addGroup(i, c) : [new FieldStack(i, c)])],
      []
    );
  }
}

const toPanel = (a: IFieldStack, data: IConfig): IPanelOptions => ({
  ...a,
  options: getOptions(a, data),
  active: true,
  hidden: false,
});

const toField = (a: IFieldStack): IFieldOptions => ({
  ...a,
  controlType: getControlType(a.type),
  validator: getValidator(a.required, a.limits?.min, a.limits?.max, a.type),
  compare: [],
  key: getKey(a.name, a.subname),
  hidden: false,
  value: getValue(a.type)(a.value, a.default, a.required),
});

export const toFormOptions = (data: IConfig): TFormOptions[] => {
  return data.config.reduce((p, c) => {
    if (c.subname) return p;
    if (c.type !== 'group') return [...p, toField(c)];
    else return [...p, toPanel(c, data)];
  }, []);
};

export const setValue = (data: IFieldStack[], v: TValue): IOutput =>
  data
    .filter((a) => !a.subname)
    .reduce(
      (p, c, i) => ({
        ...p,
        [c.name]:
          c.type === 'group'
            ? data
                .filter((a) => a.name === c.name && a.type !== 'group')
                .reduce((a, b, k) => ({ ...a, [b.subname]: v[i][k] }), {})
            : v
            ? v[i]
            : null,
      }),
      {}
    );
