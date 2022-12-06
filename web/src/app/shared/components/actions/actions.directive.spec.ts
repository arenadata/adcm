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
import { Component, DebugElement, NO_ERRORS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogModule } from '@angular/material/dialog';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ApiService } from '@app/core/api';
import { FieldService } from '@app/shared/configuration/services/field.service';

import { ActionParameters, ActionsDirective } from './actions.directive';
import { ActionMasterComponent } from '@app/shared/components';

const TestParams: ActionParameters = {
  cluster: { id: 1, hostcomponent: '' },
  actions: [
    {
      name: 'test',
      description: '',
      display_name: 'display_name_test',
      start_impossible_reason: null,
      run: 'url',
      config: null,
      hostcomponentmap: null,
      button: null,
      ui_options: null,
    },
  ],
};

@Component({
  template: '<button [appActions]="{actions: []}">ActionsTestName</button>',
})
class TestComponent {
  testParams: ActionParameters;
}

describe('ActionsDirective', () => {
  let fixture: ComponentFixture<TestComponent>;
  let component: TestComponent;
  let de: DebugElement;
  let directive: ActionsDirective;

  beforeEach(() => {
    fixture = TestBed.configureTestingModule({
      imports: [MatDialogModule, NoopAnimationsModule],
      declarations: [TestComponent, ActionsDirective],
      providers: [ActionsDirective, { provide: ApiService, useValue: {} }, { provide: FieldService, useValue: {} }],
      schemas: [NO_ERRORS_SCHEMA],
    }).createComponent(TestComponent);

    component = fixture.componentInstance;
    component.testParams = TestParams;
    de = fixture.debugElement.query(By.directive(ActionsDirective));
    directive = de.injector.get(ActionsDirective);
    fixture.detectChanges();
  });

  it('should show dialog with error message', () => {
    directive.inputData = { actions: [] /* undefined */ };
    de.triggerEventHandler('click', {});
    fixture.detectChanges();
    const result = directive.prepare();
    expect(result).toEqual({
      data: { title: 'No parameters for run the action', model: null, component: null },
    });
  });

  it('should show empty dialog with action parameters', () => {
    directive.inputData = TestParams;
    de.triggerEventHandler('click', {});
    fixture.detectChanges();
    const result = directive.prepare();
    expect(result).toEqual({
      width: '400px',
      maxWidth: '1400px',
      data: {
        title: 'Run an action [ display_name_test ]?',
        model: TestParams,
        component: ActionMasterComponent,
      },
    });
  });
});
