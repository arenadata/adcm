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
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormBuilder, FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';

import { FieldService } from '../services/field.service';
import { IYField } from '../yspec/yspec.service';
import { RootComponent } from './root.component';
import { SchemeService } from './scheme.service';

const item: IYField = {
  name: 'test',
  type: 'string',
  path: ['test'],
  controlType: 'textbox',
  validator: {},
  isInvisible: false
};

describe('RootComponent', () => {
  let component: RootComponent;
  let fixture: ComponentFixture<RootComponent>;
  let service: SchemeService;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [FormsModule, ReactiveFormsModule],
      declarations: [RootComponent],
      providers: [FieldService, FormBuilder, SchemeService],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(RootComponent);
    component = fixture.componentInstance;
    service = TestBed.inject(SchemeService);

    component.options = item;
    component.form = new FormGroup({ field: new FormControl() });
    component.value = {};
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should has form as FormGroup | FormArray | FormControl, options as IYContainer | IYField, value as TValue', () => {
    expect(component.value).toBeDefined();
    expect(component.options).toBeDefined();
    expect(component.form).toBeDefined();
  });

  xit('options type as list should displaying as list', () => {

  });
});
