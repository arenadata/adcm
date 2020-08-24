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
import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { FormBuilder, ReactiveFormsModule, FormsModule, FormGroup } from '@angular/forms';

import { FieldService } from '../field.service';
import { IYContainer } from '../yspec/yspec.service';
import { RootComponent } from './root.component';

describe('RootComponent', () => {
  let component: RootComponent;
  let fixture: ComponentFixture<RootComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [FormsModule, ReactiveFormsModule],
      declarations: [RootComponent],
      providers: [FieldService, FormBuilder],
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(RootComponent);
    component = fixture.componentInstance;

    const item: IYContainer = {
      name: 'test',
      type: 'dict',
      options: {
        name: 'test',
        path: ['test'],
        type: 'string',
        controlType: 'textbox',
        validator: {},
      },
    };
    component.options = item;
    component.form = new FormGroup({});

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
