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
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormControl, FormGroup } from '@angular/forms';

import { ItemComponent } from './item.component';
import { IControl } from './scheme.service';

describe('ItemComponent', () => {
  let component: ItemComponent;
  let fixture: ComponentFixture<ItemComponent>;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      declarations: [ItemComponent],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ItemComponent);
    component = fixture.componentInstance;
    const item: IControl = {
      name: 'test',
      type: 'string',
      rules: { name: 'test', type: 'string', path: ['test'], validator: {}, controlType: 'textbox', isInvisible: false },
      form: new FormGroup({ test: new FormControl() }),
      parent: 'dict',
      value: {},
    };
    component.item = item;
    component.invisibleItems = ['field'];
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
