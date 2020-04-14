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
import { ApiService } from '@app/core/api/api.service';
import { provideMockStore } from '@ngrx/store/testing';
import { EMPTY } from 'rxjs';

import { FieldService } from '../field.service';
import { ConfigFieldsComponent } from '../fields/fields.component';
import { ToolsComponent } from '../tools/tools.component';
import { ConfigComponent } from './main.component';
import { MainService } from './main.service';

describe('Configuration : MainComponent >> ', () => {
  let component: ConfigComponent;
  let fixture: ComponentFixture<ConfigComponent>;
  let FieldServiceStub: Partial<FieldService>;
  let MainServiceStub: Partial<MainService>;
  // let store: MockStore;

  const initialState = { socket: {} };

  beforeEach(async () => {
    FieldServiceStub = new FieldService(new FormBuilder());

    MainServiceStub = {
      getConfig: () => EMPTY,
    };

    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule],
      declarations: [ConfigComponent, ToolsComponent, ConfigFieldsComponent],
      providers: [provideMockStore({ initialState }), { provide: FieldService, useValue: FieldServiceStub }, { provide: ApiService, useValue: {} }],
      schemas: [NO_ERRORS_SCHEMA],
    })
      .overrideComponent(ConfigComponent, {
        set: {
          providers: [{ provide: MainService, useValue: MainServiceStub }],
        },
      })
      .compileComponents()
      .then(() => {
        fixture = TestBed.createComponent(ConfigComponent);
        component = fixture.componentInstance;
      });
  });

  beforeEach(() => {});

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

  /**
   * - init vars for ToolsComponent and HistoryComponent
   */
});
