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
import { MatDialog } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { ChannelService } from '@app/core';
import { ApiService } from '@app/core/api/api.service';
import { AddService } from '@app/shared/add-component/add.service';
import { provideMockStore } from '@ngrx/store/testing';

import { Much2ManyComponent } from '../much-2-many/much-2-many.component';
import { TakeService } from '../take.service';
import { ServiceHostComponent } from './service-host.component';
import { IRawHosComponent } from '../types';

const raw: IRawHosComponent = {
  hc: [
    {
      id: 1,
      host_id: 2,
      service_id: 2,
      component_id: 4,
    },
    {
      id: 2,
      host_id: 2,
      service_id: 2,
      component_id: 2,
    },
    {
      id: 3,
      host_id: 2,
      service_id: 2,
      component_id: 3,
    },
    {
      id: 4,
      host_id: 2,
      service_id: 1,
      component_id: 1,
    },
  ],
  host: [
    {
      state: 'created',
      cluster_id: 2,
      fqdn: 'bbb',
      id: 2,
      prototype_id: 18,
      provider_id: 1,
    },
  ],
  component: [
    {
      id: 1,
      name: 'NODE',
      prototype_id: 41,
      display_name: 'Taxi Node',
      constraint: null,
      requires: [],
      monitoring: 'active',
      status: 16,
      service_id: 1,
      service_name: 'GETTAXI',
      service_state: 'created',
    },
    {
      id: 2,
      name: 'UBER_SERVER',
      prototype_id: 38,
      display_name: 'UBER_SERVER',
      constraint: [1, 2],
      requires: [],
      monitoring: 'active',
      status: 16,
      service_id: 2,
      service_name: 'UBER',
      service_state: 'created',
    },
    {
      id: 3,
      name: 'UBER_NODE',
      prototype_id: 39,
      display_name: 'Simple Uber node',
      constraint: [0, '+'],
      requires: null,
      monitoring: 'active',
      status: 16,
      service_id: 2,
      service_name: 'UBER',
      service_state: 'created',
    },
    {
      id: 4,
      name: 'SLAVE',
      prototype_id: 40,
      display_name: 'Just slave',
      constraint: [0, 1],
      requires: [],
      monitoring: 'active',
      status: 16,
      service_id: 2,
      service_name: 'UBER',
      service_state: 'created',
    },
  ],
};

describe('Service Host Map Component', () => {
  let component: ServiceHostComponent;
  let fixture: ComponentFixture<ServiceHostComponent>;

  const initialState = { socket: {} };

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule],
      declarations: [ServiceHostComponent, Much2ManyComponent],
      providers: [
        TakeService,
        ChannelService,
        provideMockStore({ initialState }),
        { provide: ApiService, useValue: {} },
        { provide: AddService, useValue: {} },
        { provide: MatDialog, useValue: {} },
        Router,
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ServiceHostComponent);
    component = fixture.componentInstance;
    component.service.init(raw);
    component.hosts = component.service.Hosts;
    component.serviceComponents = component.service.Components;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeDefined();
  });

  it('should display compnents and hosts as button', () => {
    fixture.whenStable().then(() => {
      const cElement: HTMLElement = fixture.nativeElement;
      const components = cElement.querySelectorAll('.wrapper').item(0).querySelectorAll('app-much-2-many');
      const hosts = cElement.querySelectorAll('.wrapper').item(1).querySelectorAll('app-much-2-many');
      expect(hosts.length).toBe(1);
      expect(components.length).toBe(4);
      const host_relations = hosts.item(0).querySelector('.relations-list').children;
      expect(host_relations.length).toBe(4);
      components.forEach((a) => expect(a.querySelector('.relations-list').children.length).toBe(1));
    });
  });

  it('should mark host/component as selected and(or) as linked', () => {
    fixture.whenStable().then(() => {
      const cElement: HTMLElement = fixture.nativeElement;
      const components = cElement.querySelectorAll('.wrapper').item(0).querySelectorAll('app-much-2-many');
      const hosts = cElement.querySelectorAll('.wrapper').item(1).querySelectorAll('app-much-2-many');
      const host = hosts.item(0);
      (host.querySelector('.m2m .title-container button.title') as HTMLElement).click();
      fixture.detectChanges();
      expect(host.querySelector('.m2m').classList.contains('selected')).toBeTrue();
      components.forEach((a) => expect(a.querySelector('.m2m').classList.contains('linked')).toBeTrue());
    });
  });
});
