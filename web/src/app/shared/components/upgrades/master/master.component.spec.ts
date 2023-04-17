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
import { FormBuilder, FormControl, FormGroup } from '@angular/forms';
import { MatListModule } from '@angular/material/list';
import { ApiService } from '@app/core/api/api.service';
import { FieldService } from '@app/shared/configuration/services/field.service';
import { ConfigFieldsComponent } from '@app/shared/configuration/fields/fields.component';
import { ServiceHostComponent } from '@app/shared/host-components-map/services2hosts/service-host.component';
import { UpgradeMasterConfigComponent } from './upgrade-master-config.component';
import { UpgradeMasterComponent as MasterComponent } from './master.component';
import { MasterService } from './master.service';
import {IConfig} from "@app/shared/configuration/types";
import {IActionParameter, IUIOptions} from "@app/core/types";

describe('MasterComponent', () => {
  let component: MasterComponent;
  let fixture: ComponentFixture<MasterComponent>;

  let ApiServiceStub: Partial<ApiService>;
  let FieldServiceStub: Partial<FieldService>;

  beforeEach(async () => {
    ApiServiceStub = {};
    FieldServiceStub = new FieldService({} as FormBuilder);

    TestBed.configureTestingModule({
      imports: [MatListModule],
      declarations: [MasterComponent, UpgradeMasterConfigComponent],
      providers: [MasterService, {provide: ApiService, useValue: ApiServiceStub}, {
        provide: FieldService,
        useValue: FieldServiceStub
      }],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(MasterComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('input data for model property must be defined', () => {
    component.model = {upgrades: []};
    fixture.detectChanges();
    expect(component.model).toBeDefined();
  });

  it('input data for model.actons property must be array', () => {
    component.model = {upgrades: []};
    fixture.detectChanges();
    expect(component.model.upgrades).toBeDefined();
    expect(component.model.upgrades).toEqual(jasmine.any(Array));
  });

  it('should be show template if model.upgrades.length === 0', () => {
    component.model = {upgrades: []};
    fixture.detectChanges();
    const compHost: HTMLElement = fixture.debugElement.nativeElement;
    expect(compHost.querySelector('p').textContent).toBe('No data for the upgrades!');
  });

  it('should be show template for current upgrade if model.upgrades.length === 1 and config = null and host-map = null', () => {
    component.model = {
      upgrades: [{
        bundle_id: 1,
        config: null,
        description: '',
        do: 'url',
        from_edition: ['community'],
        hostcomponentmap: null,
        id: 1,
        license: '',
        license_url: '',
        max_strict: true,
        max_version: '',
        min_strict: false,
        min_version: '',
        name: '',
        display_name: '',
        state_available: '',
        state_on_success: '',
        ui_options: null,
        upgradable: true,
        url: ''
      }]
    };
    fixture.detectChanges();
    const compHost: HTMLElement = fixture.debugElement.nativeElement;
    const cancelButton = compHost.querySelector('button[color="primary"]');
    const runButton = compHost.querySelector('button[color="accent"]');
    expect(runButton).toBeTruthy();
    expect(cancelButton).toBeTruthy();
    expect(cancelButton.textContent).toContain('Cancel');
    expect(runButton.textContent).toContain('Run');
  });

  it('should be show upgrades list for choose current upgrade if model.upgrades.length > 1', () => {
    component.model = {
      upgrades: [
        {
          bundle_id: 1,
          config: {} as IConfig,
          description: '',
          do: 'url',
          from_edition: ['community'],
          hostcomponentmap: [] as IActionParameter[],
          id: 1,
          license: '',
          license_url: '',
          max_strict: true,
          max_version: '',
          min_strict: false,
          min_version: '',
          name: '',
          display_name: '',
          state_available: '',
          state_on_success: '',
          ui_options: {} as IUIOptions,
          upgradable: true,
          url: ''
        },
        {
          bundle_id: 1,
          config: {} as IConfig,
          description: '',
          do: 'url',
          from_edition: ['community'],
          hostcomponentmap: [] as IActionParameter[],
          id: 1,
          license: '',
          license_url: '',
          max_strict: true,
          max_version: '',
          min_strict: false,
          min_version: '',
          name: '',
          display_name: '',
          state_available: '',
          state_on_success: '',
          ui_options: {} as IUIOptions,
          upgradable: true,
          url: ''
        }
      ]
    };
    fixture.detectChanges();
    const compHost: HTMLElement = fixture.debugElement.nativeElement;
    // expect(compHost.querySelector('i').textContent).toBe("Let's choose first");
    const buttonsLength = compHost.querySelector('mat-action-list').getElementsByTagName('button').length;
    expect(buttonsLength).toBeGreaterThan(1);
  });

  it('should be show template for current upgrade if config exist only', () => {
    component.model = {
      upgrades: [
        {
          bundle_id: 1,
          config: {
            config: [
              {
                type: 'string',
                name: 'test',
                display_name: 'display name test',
                subname: '',
                default: null,
                value: null,
                required: false,
                description: '',
                read_only: false,
                activatable: false,
                group_config: null,
              }
            ]
          } as IConfig,
          description: '',
          do: 'url',
          from_edition: ['community'],
          hostcomponentmap: null,
          id: 1,
          license: '',
          license_url: '',
          max_strict: true,
          max_version: '',
          min_strict: false,
          min_version: '',
          name: '',
          display_name: '',
          state_available: '',
          state_on_success: '',
          ui_options: {} as IUIOptions,
          upgradable: true,
          url: ''
        }
      ]
    };
    fixture.detectChanges();
    const de = fixture.debugElement.nativeElement;
    const config = de.querySelector('app-upgrade-master-config');
    const hm = de.querySelector('app-service-host');
    expect(hm).toBeNull();
    expect(config).toBeTruthy();
  });

  it('should be show template for current upgrade if host-map exist only', () => {
    component.model = {
      upgrades: [{
        bundle_id: 1, config: null, description: '', do: 'url', from_edition: ['community'],
        hostcomponentmap: [{component: '', action: 'add', service: ''}] as IActionParameter[], id: 1, license: '',
        license_url: '', max_strict: true, max_version: '', min_strict: false, min_version: '', name: '', display_name: '',
        state_available: '', state_on_success: '', ui_options: {} as IUIOptions, upgradable: true, url: ''
      }]
    };
    fixture.detectChanges();
    const de = fixture.debugElement.nativeElement;
    const config = de.querySelector('app-upgrade-master-config');
    const hm = de.querySelector('app-service-host');
    expect(config).toBeNull();
    expect(hm).toBeTruthy();
  });

  it('should be show template for current upgrade with config and host-map', () => {
    component.model = {
      upgrades: [{
        bundle_id: 1, config: {
          config: [
            {
              type: 'string',
              name: 'test',
              display_name: 'display name test',
              subname: '',
              default: null,
              value: null,
              required: false,
              description: '',
              read_only: false,
              activatable: false,
              group_config: null,
            }
          ]
        } as IConfig, description: '', do: 'url', from_edition: ['community'],
        hostcomponentmap: [{component: '', action: 'add', service: ''}] as IActionParameter[], id: 1, license: '',
        license_url: '', max_strict: true, max_version: '', min_strict: false, min_version: '', name: '', display_name: '',
        state_available: '', state_on_success: '', ui_options: {} as IUIOptions, upgradable: true, url: ''
      }]
    };
    fixture.detectChanges();
    const de = fixture.debugElement.nativeElement;
    const config = de.querySelector('app-upgrade-master-config');
    const hm = de.querySelector('app-service-host');
    expect(config).toBeTruthy();
    expect(hm).toBeTruthy();
  });

  it('should be undefined value if ServiceHostComponent ConfigFieldComponent not exist', () => {
    const service = fixture.debugElement.injector.get(MasterService);
    const result = service.parseData(undefined);
    expect(result).toBeUndefined();
  });

  it('check value when ConfigFieldComponent exist', () => {
    const service = fixture.debugElement.injector.get(MasterService);

    const config = {
      form: new FormGroup({string_ctr: new FormControl('string_test'), bool_ctr: new FormControl(true)}),
      rawConfig: {
        config: [
          {name: 'string_ctr', type: 'string', value: 'string_test'},
          {name: 'bool_ctr', type: 'boolean', value: true}
        ]
      }
    } as ConfigFieldsComponent;

    const result = service.parseData({config});
    expect(result).toEqual({config: {string_ctr: 'string_test', bool_ctr: true}, hc: undefined, attr: undefined});
  });

  it('check value when ServiceHostComponent exist', () => {
    const service = fixture.debugElement.injector.get(MasterService);
    const hc = [{host_id: 1, service_id: 4, component_id: 1, id: 9}];
    const hostmap = {statePost: {data: hc}} as ServiceHostComponent;
    const result = service.parseData({hostmap});
    expect(result).toEqual({config: undefined, hc, attr: undefined});
  });
});
