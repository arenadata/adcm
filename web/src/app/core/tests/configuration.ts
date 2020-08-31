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
import { itemOptions } from '@app/shared/configuration/field.service';

import { ConfigValueTypes, IConfig, IConfigAttr, ILimits, stateType, TValue, IUIoptions, IFieldStack } from '../../shared/configuration/types';
import { IYContainer, IYField, IYspec } from '../../shared/configuration/yspec/yspec.service';

export const itemOptionsArr: itemOptions[] = [
  {
    required: true,
    name: 'field_string_0',
    display_name: 'display_field_string_0_',
    subname: '',
    type: 'string',
    activatable: false,
    read_only: false,
    default: null,
    value: '',
    key: 'field_string_0',
    validator: { required: true, min: null, max: null, pattern: null },
    controlType: 'textbox',
    hidden: false,
    compare: [],
  },
  {
    name: 'field_group_1',
    display_name: 'display_field_group_1_',
    subname: '',
    type: 'group',
    activatable: false,
    read_only: false,
    default: null,
    value: null,
    required: true,
    hidden: false,
    active: true,
    options: [
      {
        name: 'subname_integer_0',
        display_name: 'display_field_group_1_subname_integer_0',
        subname: 'subname_integer_0',
        type: 'integer',
        activatable: false,
        read_only: false,
        default: null,
        value: '',
        required: true,
        key: 'subname_integer_0/field_group_1',
        validator: { required: true, min: null, max: null, pattern: /^[-]?\d+$/ },
        controlType: 'textbox',
        hidden: false,
        compare: [],
      },
    ],
  },
];

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
    public type: ConfigValueTypes,
    public name: string = null,
    public value = null,
    public read_only = false,
    public required = true,
    public activatable = false
  ) {
    const dn = `field_${type}_${id}`;
    this.name = !this.name ? dn : this.name;
    this.subname = this.name === dn ? '' : `subname_${type}_${id}`;
    this.display_name = `display_${this.name}_${this.subname}`;
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
  public static addGroup(id: number, params: ConfigValueTypes[]): IFieldStack[] {
    const group = new FieldStack(id, 'group');
    return params.reduce((p, c, i) => [...p, new FieldStack(i, c, group.name)], [group]);
  }

  public static add(params: (ConfigValueTypes | ConfigValueTypes[])[]) {
    return params.reduce<IFieldStack[]>((p, c, i) => [...p, ...(Array.isArray(c) ? this.addGroup(i, c) : [new FieldStack(i, c)])], []);
  }
}
