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

import { async, TestBed, ComponentFixture } from '@angular/core/testing';
import { IssueInfoComponent } from './issue-info.component';
import { ComponentData } from './tooltip/tooltip.service';
import { EventEmitter } from '@angular/core';

class MockComponentData {
  typeName = 'cluster';
  current = { issue: { host_component: false, service: [{ id: 1, name: 'Service_Name', issue: { config: false } }] } };
  emitter = new EventEmitter();
}

describe('Issue-info component', () => {
  let fixture: ComponentFixture<IssueInfoComponent>;
  let component: IssueInfoComponent;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [IssueInfoComponent],
      providers: [{ provide: ComponentData, useClass: MockComponentData }],
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(IssueInfoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

});
