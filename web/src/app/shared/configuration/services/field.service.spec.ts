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

import { FieldService, getValue, IOutput, ISource } from './field.service';
import { Configuration, FieldFactory, setValue, toFormOptions } from '../tests/configuration';
import { IFieldStack, resultTypes, TNForm } from '../types';
import { IYContainer, IYField, IYspec } from '../yspec/yspec.service';

/**
 * inputData - data from backend for configuration IConfig.config : FieldStack[]
 * formData : itemOptions[] -  we can render the form based on inputData
 *
 * FormControl.value - user input
 * outputData - this is that we send to backend after parsing FormControl.value  - IOutput
 *
 */

describe('Configuration fields service', () => {
  let service: FieldService;
  let checkValue: (value: resultTypes, type: TNForm) => resultTypes;
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

  it('getPanels(undefined) should return undefined', () => {
    expect(service.getPanels(undefined)).toEqual(undefined);
  });

  it('getPanels({}) should return undefined', () => {
    expect(service.getPanels({} as any)).toEqual(undefined);
  });

  it('getPanels({config: []}) should return []', () => {
    expect(service.getPanels({ config: [] })).toEqual([]);
  });

  it('getPanels should transform FieldStack[] to itemOptions[]', () => {
    const inputData = new Configuration(FieldFactory.add(['string', ['integer']]));
    const formData = toFormOptions(inputData);
    const output = service.getPanels(inputData);
    expect(output).toEqual(formData);
  });

  it('toFormGroup should generate FormGroup and check value', () => {
    const inputData = new Configuration(FieldFactory.add(['string', ['integer']]));
    const formData = toFormOptions(inputData);
    const fg = service.fb.group(
      {
        field_string_0: service.fb.control(''),
        field_group_1: service.fb.group({
          subname_integer_0: ['', [Validators.required, Validators.pattern(/^[-]?\d+$/)]],
        }),
      },
      { validator: () => null }
    );
    const form = service.toFormGroup(formData);
    expect(form.value).toEqual(fg.value);
  });

  it('filterApply with search by display_name and value should change the fields satisfy search condition on as hidden', () => {
    const source = new Configuration(FieldFactory.add(['string', 'json', 'integer', 'text']));
    source.config[1].value = { key: 'string_0' };
    source.config[3].value = 'other text';
    const formOpt = toFormOptions(source);
    expect(service.filterApply(formOpt, { search: 'string_0', advanced: false }).filter((a) => !a.hidden)).toEqual([
      {
        type: 'string',
        name: 'field_string_0',
        value: '',
        required: true,
        read_only: false,
        activatable: false,
        default: null,
        subname: '',
        display_name: 'display_field_string_0_',
        controlType: 'textbox',
        validator: { required: true, min: undefined, max: undefined, pattern: null },
        compare: [],
        key: 'field_string_0',
        hidden: false,
      },
      {
        type: 'json',
        name: 'field_json_1',
        value: getValue('json')({ key: 'string_0' }),
        required: true,
        read_only: false,
        activatable: false,
        default: null,
        subname: '',
        display_name: 'display_field_json_1_',
        controlType: 'json',
        validator: { required: true, min: undefined, max: undefined, pattern: null },
        compare: [],
        key: 'field_json_1',
        hidden: false,
      },
    ]);
  });

  it('filterApply with search by display_name and value should change the fields satisfy search condition on as hidden, in case when config have group', () => {
    const source = new Configuration(FieldFactory.add(['string', ['text']]));
    source.config[2].value = 'other text';
    const formOpt = toFormOptions(source);
    expect(service.filterApply(formOpt, { search: 'string_0', advanced: false }) as any).toEqual([
      {
        type: 'string',
        name: 'field_string_0',
        value: '',
        required: true,
        read_only: false,
        activatable: false,
        default: null,
        subname: '',
        display_name: 'display_field_string_0_',
        controlType: 'textbox',
        validator: { required: true, min: undefined, max: undefined, pattern: null },
        compare: [],
        key: 'field_string_0',
        hidden: false,
      },
      {
        activatable: false,
        active: true,
        default: null,
        display_name: 'display_field_group_1_',
        hidden: true,
        name: 'field_group_1',
        read_only: false,
        required: true,
        subname: '',
        type: 'group',
        value: '',
        options: [
          {
            type: 'text',
            name: 'subname_text_0',
            value: 'other text',
            required: true,
            read_only: false,
            activatable: false,
            default: null,
            subname: 'subname_text_0',
            display_name: 'display_field_group_1_subname_text_0',
            key: 'subname_text_0/field_group_1',
            validator: { required: true, min: undefined, max: undefined, pattern: null },
            controlType: 'textarea',
            hidden: true,
            compare: [],
          },
        ],
      },
    ]);
  });

  it('parseValue(empty, empty) should return {}', () => {
    const source: IFieldStack[] = [];
    const value: IOutput = {};
    expect(service.parseValue(value, source)).toEqual({});
  });

  it('parseValue should cast the string from the form to its original type', () => {
    const source = new Configuration(
      FieldFactory.add(['string', 'integer', 'integer', 'integer', 'boolean', 'boolean', 'boolean', 'float', 'float', 'map', 'map', 'list', 'list', 'option', 'option'])
    );
    const value = setValue(source.config, ['a', 1, 0, '123', true, undefined, null, 1.2, '1.23', { key: 'value' }, 'string', ['a', 1], 'string', 'option string', 0]);
    expect(service.parseValue(value, source.config)).toEqual({
      field_string_0: 'a',
      field_integer_1: 1,
      field_integer_2: 0,
      field_integer_3: 123,
      field_boolean_4: true,
      field_boolean_5: undefined,
      field_boolean_6: null,
      field_float_7: 1.2,
      field_float_8: 1.23,
      field_map_9: Object({ key: 'value' }),
      field_map_10: 'string',
      field_list_11: ['a', 1],
      field_list_12: 'string',
      field_option_13: 'option string',
      field_option_14: 0,
    });
  });

  it('parseValue should cast the string from the form to its original type, in case when config have group', () => {
    const source = new Configuration(FieldFactory.add(['string', ['integer', 'float', 'float', 'string'], ['map', 'list', 'map', 'list', 'option'], []]));
    const value = setValue(source.config, ['a', ['12', '1.0', '1.2', ''], [null, null, 'str', 'str', 0]]);

    expect(service.parseValue(value, source.config)).toEqual({
      field_string_0: 'a',
      field_group_1: { subname_integer_0: 12, subname_float_1: 1, subname_float_2: 1.2, subname_string_3: null },
      field_group_2: {
        subname_map_0: {},
        subname_list_1: [],
        subname_map_2: 'str',
        subname_list_3: 'str',
        subname_option_4: 0
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
    expect(checkValue([], 'list')).toEqual([]);
  });

  it('List fieldType :: checkValue(["string1", "", "string2"], "list") should return ["string1", "string2"]', () => {
    expect(checkValue(['string1', '', 'string2'], 'list')).toEqual(['string1', 'string2']);
  });

  it('Map fieldType :: checkValue({"string1": "value1", "string2": "value2"}, "map") should return {"string1": "value1", "string2": "value2"}', () => {
    expect(checkValue({ string1: 'value1', string2: 'value2' }, 'map')).toEqual({
      string1: 'value1',
      string2: 'value2'
    });
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
    expect(checkValue({}, 'map')).toEqual({});
  });

  /**
   *
   * check value - mocking the click save button
   *
   */
  it('parseValue - for structure: after init with empty field and not required', () => {
    const source: ISource[] = [{
      type: 'structure',
      name: 'field',
      subname: '',
      read_only: false,
      value: null,
      limits: { rules: {} }
    }];
    const output: IOutput = { field: {} };

    const result = service.parseValue(output, source);
    expect(result).toEqual({ field: null });

    const output2: IOutput = { field: [] };

    const result2 = service.parseValue(output2, source);
    expect(result2).toEqual({ field: null });

    const output3: IOutput = { field: { field1: [] } };

    const result3 = service.parseValue(output3, source);
    expect(result3).toEqual({ field: null });
  });

  it('parseValue for structure should return list', () => {
    const rules: IYContainer | IYField = {
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

    const source = new Configuration(FieldFactory.add(['structure']));
    source.config[0].value = [{ name: 'DEFAULT', port: 9092 }];
    source.config[0].limits = { rules, yspec };
    const output = { field_structure_0: [{ name: 'DEFAULT', port: '9092' }] };
    const result = service.parseValue(output, source.config);

    expect(result).toEqual({ field_structure_0: [Object({ name: 'DEFAULT', port: 9092 })] });
  });
});
