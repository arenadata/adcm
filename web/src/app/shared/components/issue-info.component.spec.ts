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
import { EventEmitter } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { IssueInfoComponent } from './issue-info.component';
import { ComponentData } from './tooltip/tooltip.service';

class MockComponentData {
  path = 'cluster';
  current = { id: 1 };
  emitter = new EventEmitter();
}

describe('Issue-info component', () => {
  let fixture: ComponentFixture<IssueInfoComponent>;
  let component: IssueInfoComponent;
  let os = require("os");
  let hostname = os.hostname();

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RouterTestingModule],
      declarations: [IssueInfoComponent],
      providers: [{ provide: ComponentData, useClass: MockComponentData }],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(IssueInfoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('issue at the current element', () => {
    component.current.issue = { host_component: false };
    fixture.detectChanges();
    const href = fixture.nativeElement.querySelector('div:last-child a').getAttribute('href');
    const c = component.current;
    const hostlessHref = href.slice(href.indexOf(c.path)-1);
    const issueName = Object.keys(c.issue)[0];
    expect(hostlessHref).toBe(`/${c.path}/${c.id}/${issueName}`);
  });

  it('issue at the daughter elements', () => {
    component.current.issue = { service: [{ id: 1, name: 'Service_Name', issue: { config: false } }] };
    fixture.detectChanges();
    const href = fixture.nativeElement.querySelector('div:last-child a').getAttribute('href');
    const c = component.current;
    const hostlessHref = href.slice(href.indexOf(c.path)-1);
    const daughterName = Object.keys(c.issue)[0];
    const daughterObj = c.issue[daughterName][0];
    const issueName = Object.keys(daughterObj.issue)[0];
    expect(hostlessHref).toBe(`/${c.path}/${c.id}/${daughterName}/${daughterObj.id}/${issueName}`);
  });

  it('issue at the parent element', () => {
    component.current = { id: 2, cluster_id: 1, issue: { cluster: [{ id: 1, name: 'Cluster_Name', issue: { config: false } }] } };
    fixture.detectChanges();
    const href = fixture.nativeElement.querySelector('div:last-child a').getAttribute('href');
    const c = component.current;
    const parentName = Object.keys(c.issue)[0];
    const parentObj = c.issue[parentName][0];
    const hostlessHref = href.slice(href.indexOf(parentObj.path)-1);
    const issueName = Object.keys(parentObj.issue)[0];
    expect(hostlessHref).toBe(`/${parentObj.path}/${parentObj.id}/${issueName}`);
  });
});
