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
import { FormBuilder } from '@angular/forms';

import { FieldService } from './field.service';
import { ConfigResultTypes, ConfigValueTypes } from './types';

describe('Configuration fields service', () => {
  let service: FieldService;
  let checkValue: (value: ConfigResultTypes, type: ConfigValueTypes) => any;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [FormBuilder, FieldService]
    });

    service = TestBed.inject(FieldService);
    checkValue = service.checkValue;
  });

  it('service should be created', () => {
    expect(service).toBeTruthy();
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

  it('List fieldType :: checkValue("string", "list") should return TypeError', () => {
    expect(checkValue('string', 'list')).toEqual(new TypeError('FieldService::checkValue - value is not Array'));
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

  it('Map fieldType :: checkValue("string1", "map") should TypeError', () => {
    expect(checkValue('string1', 'map')).toEqual(new TypeError('FieldService::checkValue - value is not Object'));
  });
});
