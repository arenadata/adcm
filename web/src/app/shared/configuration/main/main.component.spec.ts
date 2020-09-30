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
import { FormBuilder } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { FullyRenderedService } from '@app/core';
import { TextBoxComponent } from '@app/shared/form-elements/text-box.component';
import { SharedModule } from '@app/shared/shared.module';
import { provideMockStore } from '@ngrx/store/testing';
import { EMPTY, of } from 'rxjs';

import { FieldService } from '../field.service';
import { FieldComponent } from '../field/field.component';
import { ConfigFieldsComponent } from '../fields/fields.component';
import { GroupFieldsComponent } from '../group-fields/group-fields.component';
import { ToolsComponent } from '../tools/tools.component';
import { IConfig } from '../types';
import { ConfigComponent } from './main.component';
import { MainService } from './main.service';

const rawConfig: IConfig = {
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
      value: 'some string',
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
      value: 10,
      description: '',
      required: true,
    },
  ],
};

describe('Configuration : MainComponent >> ', () => {
  let component: ConfigComponent;
  let fixture: ComponentFixture<ConfigComponent>;
  let FieldServiceStub: Partial<FieldService>;
  const initialState = { socket: {} };
  class MockMainService {
    getConfig = () => EMPTY;
    filterApply = () => { };
    getHistoryList = () => EMPTY;
    parseValue = () => { };
    send = () => EMPTY;
  }

  beforeEach(async () => {
    FieldServiceStub = new FieldService(new FormBuilder());
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, SharedModule],
      declarations: [ConfigComponent, ToolsComponent, ConfigFieldsComponent, GroupFieldsComponent, FieldComponent, TextBoxComponent],
      providers: [provideMockStore({ initialState }), { provide: FieldService, useValue: FieldServiceStub }, { provide: FullyRenderedService, useValue: { stableView: () => { } } }],
      schemas: [NO_ERRORS_SCHEMA],
    })
      .overrideComponent(ConfigComponent, {
        set: {
          providers: [{ provide: MainService, useClass: MockMainService }],
        },
      })
      .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ConfigComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should exist ToolsComponent, HistoryComponent, FieldsComponent', () => {
    fixture.detectChanges();
    const de = fixture.debugElement.nativeElement;
    const tools = de.querySelector('app-tools');
    const history = de.querySelector('app-history');
    const fields = de.querySelector('app-config-fields');
    expect(tools).toBeTruthy();
    expect(history).toBeTruthy();
    expect(fields).toBeTruthy();
  });

  it('should be Save button and it must be disabled', () => {
    fixture.detectChanges();
    const de = fixture.debugElement.nativeElement;
    const saveBtn = de.querySelector('app-tools div.control-buttons button.form_config_button_save');
    expect(saveBtn).toBeTruthy();
    expect(saveBtn.disabled).toBeTrue();
  });

  it('the save button click should initialize form again', () => {
    fixture.detectChanges();
    component.rawConfig = rawConfig;
    component.config$ = of(rawConfig);
    component.cd.detectChanges();
    component.tools.disabledSave = component.fields.form.invalid;
    component.cd.detectChanges();
    const saveBtn = fixture.nativeElement.querySelector('app-tools div.control-buttons button.form_config_button_save');
    expect(saveBtn.disabled).toBeFalse();

    saveBtn.click();
    component.cd.detectChanges();

    component.fields.form.get('group').get('field_in_group').setValue('string_not_valid');
    component.cd.detectChanges();

    expect(saveBtn.disabled).toBeTruthy();
  });
});
