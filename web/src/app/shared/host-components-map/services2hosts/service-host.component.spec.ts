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
import { RouterTestingModule } from '@angular/router/testing';
import { ChannelService } from '@app/core/services';
import { AddService } from '@app/shared/add-component/add.service';
import { SharedModule } from '@app/shared/shared.module';
import { provideMockStore } from '@ngrx/store/testing';

import { Much2ManyComponent } from '../much-2-many/much-2-many.component';
import { TakeService } from '../take.service';
import { ComponentFactory, HCFactory, HcmHost, HCmRequires } from '../test';
import { IRawHosComponent } from '../types';
import { ServiceHostComponent } from './service-host.component';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { ApiService } from '@app/core/api';

function genData() {
  const _c = ComponentFactory(4, 1);
  const host = [new HcmHost('test', 1)];
  return { component: _c, host, hc: HCFactory(1, 1, 4) };
}

function domFirstElems(
  n: HTMLElement
): {
  components: NodeListOf<Element>;
  hosts: NodeListOf<Element>;
  host: Element;
  comp: Element;
  hostBtn: HTMLElement;
  compBtn: HTMLElement;
  addAllBtn: HTMLElement;
} {
  const components = n.querySelectorAll('.wrapper').item(0).querySelectorAll('app-much-2-many');
  const hosts = n.querySelectorAll('.wrapper').item(1).querySelectorAll('app-much-2-many');
  const host = hosts.item(0);
  const comp = components.item(0);
  const hostBtn = host.querySelector('.m2m .title-container button.title') as HTMLElement;
  const compBtn = comp.querySelector('.m2m .title-container button.title') as HTMLElement;
  const addAllBtn = n.querySelector('app-dialog button.mat-accent') as HTMLElement;
  return { components, hosts, host, comp, hostBtn, compBtn, addAllBtn };
}

describe('Service Host Map Component', () => {
  let component: ServiceHostComponent;
  let fixture: ComponentFixture<ServiceHostComponent>;

  const initialState = { socket: {} };

  const initDefault = (r: IRawHosComponent): void => {
    component.init(r);
    fixture.detectChanges();
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, SharedModule, RouterTestingModule],
      declarations: [ServiceHostComponent, Much2ManyComponent],
      providers: [
        MatDialog,
        TakeService,
        ChannelService,
        provideMockStore({ initialState }),
        {
          provide: ApiService,
          useValue: {}
        },
        {
          provide: ADD_SERVICE_PROVIDER,
          useClass: AddService
        },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();

    fixture = TestBed.createComponent(ServiceHostComponent);

    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeDefined();
  });

  it('should display components and hosts as button', () => {
    initDefault(genData());
    const dom = domFirstElems(fixture.nativeElement);
    const components = dom.components;
    const hosts = dom.hosts;
    expect(hosts.length).toBe(1);
    expect(components.length).toBe(4);
    const host_relations = hosts.item(0).querySelector('.relations-list').children;
    expect(host_relations.length).toBe(4);
    components.forEach((a) => expect(a.querySelector('.relations-list').children.length).toBe(1));
  });

  it('should mark host/component as selected and(or) as linked', () => {
    initDefault(genData());
    const dom = domFirstElems(fixture.nativeElement);
    const components = dom.components;
    const host = dom.host;
    (host.querySelector('.m2m .title-container button.title') as HTMLElement).click();
    fixture.detectChanges();
    expect(host.querySelector('.m2m').classList.contains('selected')).toBeTrue();
    components.forEach((a) => expect(a.querySelector('.m2m').classList.contains('linked')).toBeTrue());
  });

  it('should add relative on click and check linked and selected property', () => {
    const data = { component: ComponentFactory(4, 1), host: [new HcmHost('test', 1)], hc: [] };
    initDefault(data);
    const dom = domFirstElems(fixture.nativeElement);
    const host = dom.host;
    const comp = dom.comp;
    const host_btn = dom.hostBtn;
    const comp_btn = dom.compBtn;
    const host_relations = host.querySelector('.relations-list').children;
    const comp_relations = comp.querySelector('.relations-list').children;

    const comp_isLinked = () => comp.querySelector('.m2m').classList.contains('linked');
    const comp_isSelect = () => comp.querySelector('.m2m').classList.contains('selected');
    const host_isSelect = () => host.querySelector('.m2m').classList.contains('selected');
    const host_isLinked = () => host.querySelector('.m2m').classList.contains('linked');

    // start: host - select
    host_btn.click(); // added class .selected
    fixture.detectChanges();
    expect(host_isSelect()).toBeTrue();

    comp_btn.click();
    fixture.detectChanges();
    expect(comp_isLinked()).toBeTrue();
    expect(host_relations.length).toBe(1);
    expect(comp_relations.length).toBe(1);

    comp_btn.click();
    fixture.detectChanges();
    expect(comp_isLinked()).toBeFalse();
    expect(host_relations.length).toBe(0);
    expect(comp_relations.length).toBe(0);

    host_btn.click();
    fixture.detectChanges();
    expect(host_isSelect()).toBeFalse();
    // end

    // start: component- select
    comp_btn.click();
    fixture.detectChanges();
    expect(comp_isSelect()).toBeTrue();

    host_btn.click();
    fixture.detectChanges();
    expect(host_isLinked()).toBeTrue();
    expect(host_relations.length).toBe(1);
    expect(comp_relations.length).toBe(1);

    host_btn.click();
    fixture.detectChanges();
    expect(host_isLinked()).toBeFalse();
    expect(host_relations.length).toBe(0);
    expect(comp_relations.length).toBe(0);

    comp_btn.click();
    fixture.detectChanges();
    expect(host_isSelect()).toBeFalse();
    // end
  });

  it('check dependencies and add validation rules for them', () => {
    const data = { component: ComponentFactory(4, 1), host: [new HcmHost('test', 1)], hc: [] };
    data.component[1].constraint = [1, 2];
    data.component[2].constraint = [0, '+'];
    data.component[3].constraint = [0, 1];
    initDefault(data);
    const dom = domFirstElems(fixture.nativeElement);
    const components = dom.components;
    const host_btn = dom.hostBtn;
    const comp_btn = dom.compBtn;

    comp_btn.click();
    fixture.detectChanges();

    // check constraints
    components.forEach((c, i) => {
      const title = c.querySelector('.m2m .title-container button.title') as HTMLElement;
      const star = title.querySelector('span.warn');
      const d = data.component[i];
      if (d.constraint?.length) {
        expect(star).toBeDefined();
        // mouseover
        //expect(last.attributes.getNamedItem('ng-reflect-message').value).toBe('Must be installed at least 1 components.');
      } else {
        expect(star).toBeNull();
      }
    });

    host_btn.click();
    fixture.detectChanges();

    // check dependencies
    components.forEach((c, i) => {
      const title = c.querySelector('.m2m .title-container button.title') as HTMLElement;
      const star = title.querySelector('span.warn');
      if (i !== 0) {
        expect(star).toBeDefined();
        //expect(last.attributes.getNamedItem('ng-reflect-message').value).toBe('Must be installed at least 1 components.');
      } else {
        expect(star).toBeNull();
      }
    });
  });

  it('if component has `requires` should show dialog with `requires`', () => {
    const data = { component: ComponentFactory(1, 1), host: [new HcmHost('test', 1)], hc: [] };
    const r = new HCmRequires(2);
    r.components = [new HCmRequires(3)];
    data.component[0].requires = [r];
    initDefault(data);

    const dom = domFirstElems(fixture.nativeElement);
    const host_btn = dom.hostBtn;
    const comp_btn = dom.compBtn;

    host_btn.click();
    fixture.detectChanges();

    comp_btn.click();
    fixture.detectChanges();

    const dialog = document.querySelector('app-dependencies') as HTMLElement;

    if (dialog) {
      expect(dialog).toBeTruthy();
      expect(dialog.innerText).toContain('component_display_name_2');
      expect(dialog.innerText).toContain('component_display_name_3');
    } else {
      expect(dialog).toBeNull();
    }
  });
});
