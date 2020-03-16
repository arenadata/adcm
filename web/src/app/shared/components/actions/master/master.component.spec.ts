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
import { MatListModule } from '@angular/material/list';
import { ApiService } from '@app/core/api';
import { FieldService } from '@app/shared/configuration/field.service';

import { ActionMasterComponent as MasterComponent } from './master.component';

describe('MasterComponent', () => {
  let component: MasterComponent;
  let fixture: ComponentFixture<MasterComponent>;
  let ApiServiceStub: Partial<ApiService>;
  let FieldServiceStub: Partial<FieldService>;

  beforeEach(async(() => {
    ApiServiceStub = {};
    FieldServiceStub = {};

    TestBed.configureTestingModule({
      imports: [MatListModule],
      declarations: [MasterComponent],
      providers: [
        { provide: ApiService, useValue: ApiServiceStub },
        { provide: FieldService, useValue: FieldServiceStub }
      ]
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(MasterComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('input data for model property must be defined', () => {
    component.model = { actions: [] };
    fixture.detectChanges();
    expect(component.model).toBeDefined();
  });

  it('input data for model.actons property must be array', () => {
    component.model = { actions: [] };
    fixture.detectChanges();
    expect(component.model.actions).toBeDefined();
    expect(component.model.actions).toEqual(jasmine.any(Array));
  });

  it('should be show template if model.actions.length === 0', () => {
    component.model = { actions: [] };
    fixture.detectChanges();
    const compHost: HTMLElement = fixture.nativeElement;
    expect(compHost.querySelector('p').textContent).toBe('No data for the action!');
  });

  it('should be show template for current action if model.actions.length === 1', () => {
    component.model = {
      actions: [{ name: 'a1', display_name: 'display a1', run: 'url a1', ui_options: null, config: null, hostcomponentmap: null, button: null }]
    };
    fixture.detectChanges();
    const compHost: HTMLElement = fixture.nativeElement;
    const cancelButton = compHost.querySelector('button[color="primary"]');
    expect(cancelButton).toBeTruthy();
    expect(cancelButton.textContent).toContain('Cancel');
    const runButton = compHost.querySelector('button[color="accent"]');
    expect(runButton).toBeTruthy();
    expect(runButton.textContent).toContain('Run');
  });

  it('should be show actions list for choose current action if model.actions.length > 1', () => {
    component.model = {
      actions: [
        { name: 'a1', display_name: 'display a1', run: 'url a1', ui_options: null, config: null, hostcomponentmap: null, button: null },
        { name: 'a2', display_name: 'display a2', run: 'url a2', ui_options: null, config: null, hostcomponentmap: null, button: null }
      ]
    };
    fixture.detectChanges();
    const compHost: HTMLElement = fixture.nativeElement;
    expect(compHost.querySelector('i').textContent).toBe("Let's choose first");
    const buttonsLength = compHost.querySelector('mat-action-list').getElementsByTagName('button').length;
    expect(buttonsLength).toBeGreaterThan(1);
  });

  xit('should be show template for current action if config exist only', () => {
    component.model = {
      actions: [{ name: 'a1', display_name: 'display a1', run: 'url a1', ui_options: null, config: { config: [] }, hostcomponentmap: null, button: null }]
    };
    fixture.detectChanges();


  });

  /**
   *
   * simple template - show
   *   - config template
   *   - host-map template
   *   - master with step config -> host-map
   *
   * ui_options { confirm: string } - ActionsDirective by init dialog
   * 
   * button parameter - name action
   *
   * run button - get value from everything components, have to parse it and send post
   *
   */
});
