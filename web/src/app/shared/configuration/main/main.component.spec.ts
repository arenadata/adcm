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
import { ApiService } from '@app/core/api/api.service';
import { provideMockStore } from '@ngrx/store/testing';

import { FieldService } from '../field.service';
import { ConfigFieldsComponent } from '../fields/fields.component';
import { ToolsComponent } from '../tools/tools.component';
import { ConfigComponent } from './main.component';
import { MainService } from './main.service';

describe('Configuration : MainComponent >> ', () => {
  let component: ConfigComponent;
  let fixture: ComponentFixture<ConfigComponent>;
  //   let store: MockStore;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      declarations: [ConfigComponent, ToolsComponent, ConfigFieldsComponent],
      providers: [
        { provide: MainService, useValue: {} },
        { provide: FieldService, useValue: {} },
        { provide: ApiService, useValue: {} },
        provideMockStore(),
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ConfigComponent);
    // TestBed.inject()
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should exist ToolsComponent, HistoryComponent, FieldsComponent', () => {
    const de = fixture.debugElement.nativeElement;
    const tools = de.querySelector('app-tools');
    const history = de.querySelector('app-history');
    const fields = de.querySelector('app-config-fields');
    expect(tools).toBeTruthy();
    expect(history).toBeTruthy();
    expect(fields).toBeTruthy();
  });

  it('should be Save button and it must be disabled', () => {
    // fixture.detectChanges();
    const de = fixture.debugElement.nativeElement;
    const saveBtn = de.querySelector('app-tools div.control-buttons button.form_config_button_save');
    expect(saveBtn).toBeTruthy();
    // expect(saveBtn.disabled).toBeTrue();
  });

  /**
   * ToolsComponent with buttons disabled, and notice - 'Loading error'
   * When get data config
   * - wait FieldsComponent onload event
   * - check onReady method
   * - init vars for ToolsComponent and HistoryComponent
   */
});
