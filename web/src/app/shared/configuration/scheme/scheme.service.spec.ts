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

import { SchemeService } from './scheme.service';
import { FieldService } from '../field.service';
import { FormGroup, FormControl, FormArray } from '@angular/forms';
import { IFieldOptions } from '../types';

const form = new FormGroup({ field: new FormControl() });
const field = (<unknown>{ display_name: 'field_display_name', name: 'field', limits: {}, required: true, value: null, default: null }) as IFieldOptions;

describe('SchemeService', () => {
  let service: SchemeService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [SchemeService, { provide: FieldService, useValue: {} }] });
    service = TestBed.inject(SchemeService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('setCurrentForm with type as dict should return FormGroup', () => {
    const b = service.setCurrentForm('dict', form, field) as FormGroup;
    expect(b.controls).toEqual(jasmine.any(Object));
    expect(b instanceof FormGroup).toBeTrue();
  });

  it('setCurrentForm with type as list should return FormArray', () => {
    const b = service.setCurrentForm('list', form, field) as FormArray;
    expect(b.controls).toEqual([]);
    expect(b instanceof FormArray).toBeTrue();
  });

  it('setCurrentForm with type not list or dict should return FormControl', () => {
    const b = service.setCurrentForm('string', form, field) as any;
    expect(b.controls).toBeUndefined();
    expect(b instanceof FormControl).toBeTrue();
  });

  it('setCurrentForm with field is required should has errors {isEmpty: true}', () => {
    const b = service.setCurrentForm('string', form, field) as any;
    expect(b.errors).toEqual({isEmpty: true});
  });
});
