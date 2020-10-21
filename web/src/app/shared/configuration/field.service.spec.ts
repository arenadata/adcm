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
import { TestBed } from '@angular/core/testing';
import { FormBuilder, Validators } from '@angular/forms';

import { FieldService, IOutput, itemOptions, ISource } from './field.service';
import { ConfigValueTypes, FieldStack, IConfig, ILimits, resultTypes } from './types';
import { IYspec } from './yspec/yspec.service';

/**
 * inputData - data from backend for configuration IConfig.config : FieldStack[]
 *           => data4form : itemOptions[] we can render the form based on this data
 *
 * FormControl.value - user input
 * outputData - this is that we send to backend after parsing FormControl.value  - IOutput
 *
 */

const inputData: IConfig = {
  attr: {},
  config: [
    {
      name: 'field_string',
      display_name: 'display_name',
      subname: '',
      type: 'string',
      activatable: false,
      read_only: false,
      default: null,
      value: null,
      description: '',
      required: false,
    },
    {
      name: 'group',
      display_name: 'group_display_name',
      subname: '',
      type: 'group',
      activatable: false,
      read_only: false,
      default: null,
      value: null,
      description: '',
      required: false,
    },
    {
      name: 'group',
      display_name: 'field_in_group_display_name',
      subname: 'field_in_group',
      type: 'integer',
      activatable: false,
      read_only: false,
      default: 10,
      value: null,
      description: '',
      required: true,
    },
  ],
};

const data4form: itemOptions[] = [
  {
    required: false,
    name: 'field_string',
    display_name: 'display_name',
    subname: '',
    type: 'string',
    activatable: false,
    read_only: false,
    default: null,
    value: '',
    description: '',
    key: 'field_string',
    validator: { required: false, min: undefined, max: undefined, pattern: null },
    controlType: 'textbox',
    hidden: false,
    compare: [],
  },
  {
    name: 'group',
    display_name: 'group_display_name',
    subname: '',
    type: 'group',
    activatable: false,
    read_only: false,
    default: null,
    value: null,
    description: '',
    required: false,
    hidden: false,
    active: true,
    options: [
      {
        name: 'field_in_group',
        display_name: 'field_in_group_display_name',
        subname: 'field_in_group',
        type: 'integer',
        activatable: false,
        read_only: false,
        default: 10,
        value: '',
        description: '',
        required: true,
        key: 'field_in_group/group',
        validator: { required: true, min: undefined, max: undefined, pattern: /^[-]?\d+$/ },
        controlType: 'textbox',
        hidden: false,
        compare: [],
      },
    ],
  },
];

const data4form_simple = [
  {
    required: false,
    name: 'field_string',
    display_name: 'display_name',
    subname: '',
    type: 'string',
    activatable: false,
    read_only: false,
    default: null,
    value: '',
    description: '',
    key: 'field_string',
    validator: { required: false, min: null, max: null, pattern: null },
    controlType: 'textbox',
    hidden: false,
    compare: [],
  },
];

describe('Configuration fields service', () => {
  let service: FieldService;
  let checkValue: (value: resultTypes, type: ConfigValueTypes) => resultTypes;
  // let parseValue: (value: IOutput, source: Partial<FieldStack>[]) => IOutput;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [FormBuilder, FieldService],
    });

    service = TestBed.inject(FieldService);
    checkValue = service.checkValue;
  });

  it('service should be created', () => {
    expect(service).toBeTruthy();
  });

  it('Prepare data for configuration: getPanels(undefined) should return undefined', () => {
    expect(service.getPanels(undefined)).toEqual(undefined);
  });

  it('Prepare data for configuration: getPanels({}) should return undefined', () => {
    expect(service.getPanels({} as any)).toEqual(undefined);
  });

  it('Prepare data for configuration: getPanels({config: []}) should return []', () => {
    expect(service.getPanels({ config: [] })).toEqual([]);
  });

  it('FieldStack[] (input data IConfig.config) transform to itemOptions[] by getPanels()', () => {
    expect(service.getPanels(inputData)).toEqual(data4form);
  });

  it('Generate FormGroup : toFormGroup() check value', () => {
    const fg = service.fb.group(
      {
        field_string: service.fb.control(''),
        group: service.fb.group({
          field_in_group: ['', [Validators.required, Validators.pattern(/^[-]?\d+$/)]],
        }),
      },
      { validator: () => null }
    );
    const form = service.toFormGroup(data4form);
    expect(form.value).toEqual(fg.value);
  });

  it('Check result : parseValue(empty, empty) should return {}', () => {
    const source: FieldStack[] = [];
    const value: IOutput = {};
    expect(service.parseValue(value, source)).toEqual({});
  });

  it('Check result : parseValue(form without grop)', () => {
    const source: { name: string; subname: string; type: ConfigValueTypes; read_only: boolean; limits?: ILimits; value: any }[] = [
      { name: 'field_string', type: 'string', read_only: false, subname: '', value: '' },
      { name: 'field_int', type: 'integer', read_only: false, subname: '', value: '' },
      { name: 'field_int_as_str', type: 'integer', read_only: false, subname: '', value: '' },
      { name: 'field_int_0', type: 'integer', read_only: false, subname: '', value: '' },
      { name: 'field_float', type: 'float', read_only: false, subname: '', value: '' },
      { name: 'field_float_as_str', type: 'float', read_only: false, subname: '', value: '' },
      { name: 'field_bool', type: 'boolean', read_only: false, subname: '', value: '' },
      { name: 'field_bool_undefined', type: 'boolean', read_only: false, subname: '', value: '' },
      { name: 'field_bool_null', type: 'boolean', read_only: false, subname: '', value: '' },
      { name: 'field_json', type: 'json', read_only: false, subname: '', value: '' },
      { name: 'field_map', type: 'map', read_only: false, subname: '', value: '' },
      { name: 'field_map_empty', type: 'map', read_only: false, subname: '', value: '' },
      { name: 'field_map_not_object', type: 'map', read_only: false, subname: '', value: '' },
      { name: 'field_list', type: 'list', read_only: false, subname: '', value: '' },
      { name: 'field_list_empty', type: 'list', read_only: false, subname: '', value: '' },
      { name: 'field_list_not_array', type: 'list', read_only: false, subname: '', value: '' },
      { name: 'field_option_str', type: 'option', read_only: false, subname: '', value: '' },
      { name: 'field_option_int', type: 'option', read_only: false, subname: '', value: '' },
      // { name: 'field_option_float', type: 'option', read_only: false },
      { name: 'field_null', type: 'string', read_only: false, subname: '', value: '' },
      { name: 'field_readonly', type: 'float', read_only: true, subname: '', value: '' },
    ];
    const value: IOutput = {
      field_string: 'a',
      field_int: 1,
      field_int_0: 0,
      field_int_as_str: '123',
      field_bool: true,
      field_bool_undefined: undefined,
      field_bool_null: null,
      field_float: 1.2,
      field_float_as_str: '1.23',
      field_json: {},
      field_map: { key: 'value' },
      field_map_empty: {},
      field_map_not_object: 'string',
      field_list: ['a', 1],
      field_list_empty: [],
      field_list_not_array: 'string',
      field_option_str: 'option string',
      field_option_int: 0,
      field_null: '',
      field_readonly: 'readonly string',
    };
    expect(service.parseValue(value, source)).toEqual({
      field_string: 'a',
      field_int: 1,
      field_int_0: 0,
      field_int_as_str: 123,
      field_bool: true,
      field_bool_undefined: undefined,
      field_bool_null: null,
      field_float: 1.2,
      field_float_as_str: 1.23,
      field_map: { key: 'value' },
      field_list: ['a', 1],
      field_option_str: 'option string',
      field_option_int: 0,
      field_map_not_object: 'string',
      field_list_not_array: 'string',
      field_json: null,
      field_null: null,
      field_map_empty: null,
      field_list_empty: null,
    });
  });

  it('Check result : parseValue(form with grop)', () => {
    const source: { name: string; subname: string; type: ConfigValueTypes; read_only: boolean; limits?: ILimits; value: any }[] = [
      { name: 'field_string', type: 'string', read_only: false, subname: '', value: '' },
      { name: 'group_1', subname: '', type: 'group', read_only: false, value: '' },
      { name: 'group_1', subname: 'field_int', type: 'integer', read_only: false, value: '' },
      { name: 'group_1', subname: 'field_int_as_str', type: 'integer', read_only: false, value: '' },
      { name: 'group_1', subname: 'field_int_0', type: 'integer', read_only: false, value: '' },
      { name: 'group_1', subname: 'field_float', type: 'float', read_only: false, value: '' },
      { name: 'group_1', subname: 'field_float_as_str', type: 'float', read_only: false, value: '' },
      { name: 'field_bool', type: 'boolean', read_only: false, subname: '', value: '' },
      { name: 'field_bool_undefined', type: 'boolean', read_only: false, subname: '', value: '' },
      { name: 'field_bool_null', type: 'boolean', read_only: false, subname: '', value: '' },
      { name: 'group_2', type: 'group', read_only: false, subname: '', value: '' },
      { subname: 'field_json', name: 'group_2', type: 'json', read_only: false, value: '' },
      { subname: 'field_map', name: 'group_2', type: 'map', read_only: false, value: '' },
      { subname: 'field_map_empty', name: 'group_2', type: 'map', read_only: false, value: '' },
      { subname: 'field_map_not_object', name: 'group_2', type: 'map', read_only: false, value: '' },
      { subname: 'field_list', name: 'group_2', type: 'list', read_only: false, value: '' },
      { subname: 'field_list_empty', name: 'group_2', type: 'list', read_only: false, value: '' },
      { subname: 'field_list_not_array', name: 'group_2', type: 'list', read_only: false, value: '' },
      { subname: 'field_option_str', name: 'group_2', type: 'option', read_only: false, value: '' },
      { subname: 'field_option_int', name: 'group_2', type: 'option', read_only: false, value: '' },
      // { name: 'field_option_float', type: 'option', read_only: false },
      { subname: 'field_null', name: 'group_2', type: 'string', read_only: false, value: '' },
      { subname: 'field_readonly', name: 'group_2', type: 'float', read_only: true, value: '' },
      { name: 'group_3', type: 'group', read_only: false, subname: '', value: '' },
      { subname: 'field_readonly', name: 'group_3', read_only: true, value: '###', type: 'string' },
      { subname: 'field_empty_readonly', name: 'group_3', read_only: true, value: '', type: 'string' },
    ];
    /** form value after user input */

    const value: IOutput = {
      field_string: 'a',
      group_1: {
        field_int: 1,
        field_int_0: 0,
        field_float: 1.2,
        field_int_as_str: '123',
        field_float_as_str: '1.23',
      },
      field_bool: true,
      field_bool_undefined: undefined,
      field_bool_null: null,
      group_2: {
        field_json: null,
        field_map_empty: null,
        field_list_empty: null,
        field_map: { key: 'value' },
        field_map_not_object: 'string',
        field_list: ['a', 1],
        field_list_not_array: 'string',
        field_option_str: 'option string',
        field_option_int: 0,
        field_null: '',
        field_readonly: 'readonly string',
      },
      group_3: {},
    };
    expect(service.parseValue(value, source)).toEqual({
      field_string: 'a',
      group_1: {
        field_int: 1,
        field_int_0: 0,
        field_float: 1.2,
        field_int_as_str: 123,
        field_float_as_str: 1.23,
      },
      field_bool: true,
      field_bool_undefined: undefined,
      field_bool_null: null,
      group_2: {
        field_json: null,
        field_map_empty: null,
        field_list_empty: null,
        field_map: { key: 'value' },
        field_list: ['a', 1],
        field_option_str: 'option string',
        field_option_int: 0,
        field_map_not_object: 'string',
        field_list_not_array: 'string',
        field_null: null,
      },
    });
  });

  it('checkValue("", "string") should return null', () => {
    expect(checkValue('', 'string')).toBeNull();
  });

  it('checkValue("2.0", "float") should return 2', () => {
    expect(checkValue('2.0', 'float')).toBe(2);
  });

  it('checkValue("2.2", "float") should return 2.2', () => {
    expect(checkValue('2.2', 'float')).toBe(2.2);
  });

  it('checkValue("0", "float") should return 0', () => {
    expect(checkValue('0', 'float')).toBe(0);
  });

  it('checkValue("", "float") should return null', () => {
    expect(checkValue('', 'float')).toBeNull();
  });

  it('checkValue("23456778", "integer") should return 23456778', () => {
    expect(checkValue('23456778', 'integer')).toBe(23456778);
  });

  it('checkValue("0", "integer") should return 0', () => {
    expect(checkValue('0', 'integer')).toBe(0);
  });

  it('checkValue("", "integer") should return null', () => {
    expect(checkValue('', 'integer')).toBeNull();
  });

  it('checkValue("12345678", "option") should return 12345678', () => {
    expect(checkValue('12345678', 'option')).toBe(12345678);
  });

  it('checkValue("default", "option") should return "default"', () => {
    expect(checkValue('default', 'option')).toBe('default');
  });

  it('checkValue("0 one two", "option") should return "0 one two"', () => {
    expect(checkValue('0 one two', 'option')).toBe('0 one two');
  });

  it('checkValue("0", "option") should return 0', () => {
    expect(checkValue('0', 'option')).toBe(0);
  });

  it('checkValue("", "option") should return null', () => {
    expect(checkValue('', 'option')).toBeNull();
  });

  it('checkValue(true, "boolean") should return true', () => {
    expect(checkValue(true, 'boolean')).toBeTrue();
  });

  it('checkValue(false, "boolean") should return false', () => {
    expect(checkValue(false, 'boolean')).toBeFalse();
  });

  it('checkValue(null, "boolean") should return null', () => {
    expect(checkValue(null, 'boolean')).toBeNull();
  });

  it('checkValue("", "boolean") should return null', () => {
    expect(checkValue('', 'boolean')).toBeNull();
  });

  it('checkValue("{}", "json") should return {}', () => {
    expect(checkValue('{}', 'json')).toEqual({});
  });

  it('checkValue("", "json") should return null', () => {
    expect(checkValue('', 'json')).toBeNull();
  });

  it('checkValue(null, "json") should return null', () => {
    expect(checkValue(null, 'json')).toBeNull();
  });

  it('checkValue("{↵    "a": 23 ↵}", "json") should return { "a": 23 }', () => {
    expect(checkValue('{"a": 23 }', 'json')).toEqual({ a: 23 });
  });

  it('List fieldType :: checkValue("some string", "list") should return "some string"', () => {
    expect(checkValue('some string', 'list')).toEqual('some string');
  });

  it('List fieldType :: checkValue("[]", "list") should return null', () => {
    expect(checkValue([], 'list')).toBeNull();
  });

  it('List fieldType :: checkValue(["string1", "", "string2"], "list") should return ["string1", "string2"]', () => {
    expect(checkValue(['string1', '', 'string2'], 'list')).toEqual(['string1', 'string2']);
  });

  it('Map fieldType :: checkValue({"string1": "value1", "string2": "value2"}, "map") should return {"string1": "value1", "string2": "value2"}', () => {
    expect(checkValue({ string1: 'value1', string2: 'value2' }, 'map')).toEqual({ string1: 'value1', string2: 'value2' });
  });

  it('Map fieldType :: checkValue({"string1": "", "string2": "value2"}, "map") should return { "string1": "","string2": "value2"}', () => {
    expect(checkValue({ string1: '', string2: 'value2' }, 'map')).toEqual({ string1: '', string2: 'value2' });
  });

  it('Map fieldType :: checkValue({"": "value1", "string2": "value2"}, "map") should return {"string2": "value2"}', () => {
    expect(checkValue({ '': 'value1', string2: 'value2' }, 'map')).toEqual({ string2: 'value2' });
  });

  it('Map fieldType :: checkValue(["string1", "string2"], "map") should return { 0: "string1", 1: "string2" }', () => {
    expect(checkValue(['string1', 'string2'], 'map')).toEqual({ 0: 'string1', 1: 'string2' });
  });

  it('Map fieldType :: checkValue("some string", "map") should return "some string"', () => {
    expect(checkValue('some string', 'map')).toEqual('some string');
  });

  it('Map fieldType :: checkValue("{}", "map") should return null', () => {
    expect(checkValue({}, 'map')).toBeNull();
  });

  /**
   *
   * check value - mocking the click save button
   *
   */
  it('parseValue - for structure: after init with empty field with not required', () => {
    const source: ISource[] = [{ type: 'structure', name: 'field', subname: '', read_only: false, value: null, limits: { rules: {} } }];
    const output: IOutput = { field: {} };

    const result = service.parseValue(output, source);
    expect(result).toEqual({ field: null });

    const output2: IOutput = { field: [] };

    const result2 = service.parseValue(output2, source);
    expect(result2).toEqual({ field: null });
  });

  it('parseValue - for structure: list', () => {
    const rules = {
      name: 'root',
      type: 'list',
      options: {
        name: 'listener',
        type: 'dict',
        options: [
          {
            controlType: 'textbox',
            name: 'name',
            path: ['name', 'listener'],
            type: 'string',
            validator: {
              pattern: null,
              required: true,
            },
          },
          {
            controlType: 'textbox',
            name: 'port',
            path: ['port', 'listener'],
            type: 'int',
            validator: { required: true, pattern: /^[-]?\d+$/ },
          },
          { name: 'ssl enable', type: 'bool', path: [], controlType: 'boolean', validator: {} },
          { name: 'sasl protocol', type: 'string', path: [], controlType: 'textbox', validator: {} },
        ],
      },
    };

    const yspec: IYspec = {
      boolean: { match: 'bool' },
      integer: { match: 'int' },
      string: { match: 'string' },
      root: {
        match: 'list',
        item: 'listener',
      },
      listener: {
        items: {
          name: 'string',
          port: 'integer',
          'sasl protocol': 'string',
          'ssl enable': 'boolean',
        },
        match: 'dict',
        required_items: ['name', 'port'],
      },
    };

    const source: ISource[] = [
      {
        limits: {
          rules,
          yspec,
        },
        name: 'listeners',
        read_only: false,
        subname: '',
        type: 'structure',
        value: [{ name: 'DEFAULT', port: 9092 }],
      },
    ];

    const output = { listeners: [{ name: 'DEFAULT', port: '9092' }] };
    const result = service.parseValue(output, source);

    expect(result).toEqual({ listeners: [{ name: 'DEFAULT', port: 9092 }] });
  });
});
