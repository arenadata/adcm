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
import { TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { Component } from '@app/core/types';

import { ApiService } from '../../core/api';
import { AddService } from '../add-component/add.service';
import { TakeService } from './take.service';
import { CompTile } from './types';

const ctData: Component = {
  id: 1,
  prototype_id: 3,
  service_id: 2,
  service_name: 'test_service',
  service_state: 'created',
  name: 'test',
  display_name: 'test',
  status: 16,
  constraint: '',
  monitoring: 'passive',
};

describe('HostComponentsMap :: TakeService', () => {
  let service: TakeService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [{ provide: ApiService, useValue: {} }, { provide: AddService, useValue: {} }, { provide: MatDialog, useValue: {} }, TakeService],
    });
    service = TestBed.inject(TakeService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  xit('fillHost() should return HostTile[] by response result', () => {

  });

  xit('fillComponennt() should return CompTile[] by response result', () => {

  });

  xit('setRelations() should detect relations between host-component by response result', () => {

  });

  xit('next() should set needed attributes for host or component', () => {

  });

  xit('divorce() should remove property from host or component', () => {

  });

  it('validateConstraints fn should be null if argument is null', () => {
    const mCompTile = new CompTile(ctData);
    expect(service.validateConstraints(mCompTile, 0)()).toBeNull();
  });

  it('validateConstraints fn for Component.constrant = [0, 1] to be null', () => {
    const d = { ...ctData, constraint: [0, 1] };
    const mCompTile = new CompTile(d);
    expect(service.validateConstraints(mCompTile, 0)()).toBeNull();
  });

  it('validateConstraints fn for Component.constrant = [0, +] to be null', () => {
    const d = { ...ctData, constraint: [0, '+'] };
    const mCompTile = new CompTile(d);
    expect(service.validateConstraints(mCompTile, 0)()).toBeNull();
  });

  it('validateConstraints fn for Component.constrant = [1]', () => {
    const d = { ...ctData, constraint: [1] };
    const mCompTile = new CompTile(d);
    expect(service.validateConstraints(mCompTile, 0)()).toEqual({ error: 'Exactly 1 component should be installed' });
  });

  it('validateConstraints fn for Component.constrant = [1, 2]', () => {
    const d = { ...ctData, constraint: [1, 2] };
    const mCompTile = new CompTile(d);
    expect(service.validateConstraints(mCompTile, 0)()).toEqual({ error: 'Must be installed at least 1 components.' });
  });

  it('validateConstraints fn for Component.constrant = [1, +]', () => {
    const d = { ...ctData, constraint: [1, '+'] };
    const mCompTile = new CompTile(d);
    expect(service.validateConstraints(mCompTile, 0)()).toEqual({ error: 'Must be installed at least 1 components.' });
  });

  it('validateConstraints fn for Component.constrant = [odd]', () => {
    const d = { ...ctData, constraint: ['odd'] };
    const mCompTile = new CompTile(d);
    expect(service.validateConstraints(mCompTile, 0)()).toEqual({ error: 'One or more component should be installed. Total amount should be odd.' });
  });

  it('validateConstraints fn for Component.constrant = [1, odd]', () => {
    const d = { ...ctData, constraint: [1, 'odd'] };
    const mCompTile = new CompTile(d);
    expect(service.validateConstraints(mCompTile, 0)()).toEqual({ error: 'Must be installed at least 1 components. Total amount should be odd.' });
  });

  it('validateConstraints fn for Component { constrant: [3, odd], relations: [{}]} =>  Must be installed at least 3 components. Total amount should be odd.', () => {
    const d = { ...ctData, constraint: [3, 'odd'] };
    const mCompTile = new CompTile(d);
    mCompTile.relations = [{ id: 0, name: 'test', relations: [], color: 'none', disabled: false }];
    expect(service.validateConstraints(mCompTile, 0)()).toEqual({ error: 'Must be installed at least 3 components. Total amount should be odd.' });
  });

  it('validateConstraints fn for Component { constrant: [0, odd], relations: [{}, {}]} =>  Total amount should be odd.', () => {
    const d = { ...ctData, constraint: [0, 'odd'] };
    const mCompTile = new CompTile(d);
    (mCompTile.relations = [
      { id: 0, name: 'test', relations: [], color: 'none', disabled: false },
      { id: 1, name: 'test', relations: [], color: 'none', disabled: false },
    ]),
      expect(service.validateConstraints(mCompTile, 0)()).toEqual({ error: 'Total amount should be odd.' });
  });

  it('validateConstraints fn for Component { constrant: [1, odd], relations: [{}]}] tobe null', () => {
    const d = { ...ctData, constraint: [1, 'odd'] };
    const mCompTile = new CompTile(d);
    mCompTile.relations = [{ id: 0, name: 'test', relations: [], color: 'none', disabled: false }];
    expect(service.validateConstraints(mCompTile, 0)()).toBeNull();
  });

  it('validateConstraints fn for Component.constrant = [+]', () => {
    const d = { ...ctData, constraint: ['+'] };
    const mCompTile = new CompTile(d);
    //compone.Hosts = [{ id: 0, name: 'test', relations: [], color: 'none', disabled: false }];
    expect(service.validateConstraints(mCompTile, 1)()).toEqual({ error: 'Component should be installed on all hosts of cluster.' });
  });
});
