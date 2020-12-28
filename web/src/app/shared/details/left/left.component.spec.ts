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
import { Component, NO_ERRORS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { Job } from '@app/core/types';
import { MaterialModule } from '@app/shared/material.module';
import { StuffModule } from '@app/shared/stuff.module';

import { NavigationService } from '../navigation.service';
import { LeftComponent } from './left.component';

@Component({})
class ExampleComponent {}

describe('LeftComponent', () => {
  let component: LeftComponent;
  let fixture: ComponentFixture<LeftComponent>;
  const issueIcon = (name: string) => fixture.nativeElement.querySelector(`a[adcm_test=tab_${name}] div mat-icon`);

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [MaterialModule, StuffModule, RouterTestingModule.withRoutes([{ path: '1', component: ExampleComponent }])],
      declarations: [LeftComponent],
      providers: [NavigationService],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();
  });

  beforeEach(() => {
    // spyOn(router, 'navigate').and.callFake(() => { });
    fixture = TestBed.createComponent(LeftComponent);
    component = fixture.componentInstance;
    component.current = { typeName: 'cluster' };
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize menu', () => {
    const el: HTMLElement = fixture.debugElement.nativeElement;
    const list = el.querySelectorAll('a');
    expect(list.length).toBeGreaterThan(0);
  });

  it('check issue: if item have issue should display icon <priority_hight> name', () => {
    component.current = { typeName: 'cluster', issue: { config: false } };
    fixture.detectChanges();
    const icon = issueIcon('config');
    expect(icon).toBeTruthy();
    expect(icon.innerText).toBe('priority_hight');
  });

  it('clear issue should not display icon <priority_hight> name', () => {
    component.current = { typeName: 'cluster', issue: { config: false } };
    fixture.detectChanges();
    const icon = issueIcon('config');
    expect(icon).toBeTruthy();
    component.issue = {};
    fixture.detectChanges();
    const icon1 = issueIcon('config');
    expect(icon1).toBeFalsy();
  });

  it('raise issue should display icon <priority_hight> name', () => {
    component.current = { typeName: 'cluster' };
    fixture.detectChanges();
    const icon = issueIcon('config');
    expect(icon).toBeFalsy();
    component.issue = { config: false };
    fixture.detectChanges();
    const icon1 = issueIcon('config');
    expect(icon1).toBeTruthy();
  });

  it('if the item have status === 0 should show <check_circle_outline> icon', () => {
    component.current = { typeName: 'cluster', status: 0 };
    fixture.detectChanges();
    const icon = issueIcon('status');
    expect(icon).toBeTruthy();
    expect(icon.innerText).toBe('check_circle_outline');
  });

  it('if the item have status !== 0 should show <error_outline> icon', () => {
    component.current = { typeName: 'cluster', status: 16 };
    fixture.detectChanges();
    const icon = issueIcon('status');
    expect(icon).toBeTruthy();
    expect(icon.innerText).toBe('error_outline');
  });

  // for jobs only
  it('if the item have action should add button-icon with specific name <cloud_download> (todo: custom name)', () => {
    component.current = { typeName: 'job', log_files: [{ name: 'Test', type: 'type_test', id: 1, download_url: 'download_url_test' }] } as Job;
    fixture.detectChanges();
    const list = fixture.nativeElement.querySelectorAll('a');
    expect(list.length).toBe(2); // main, test
    expect(list[0].querySelector('div span').innerText).toBe('Main');
    expect(list[1].querySelector('div span').innerText).toBe('Test [ type_test ]');
    expect(list[1].querySelector('div button')).toBeTruthy();
    expect(list[1].querySelector('div button span mat-icon').innerText).toBe('cloud_download');
  });

  it('if the item has an action, then this property should be a function and a click should call this function', () => {
    component.current = { typeName: 'job', log_files: [{ name: 'Test', type: 'type_test', id: 1, download_url: 'download_url_test' }] } as Job;
    fixture.detectChanges();
    const list = fixture.nativeElement.querySelectorAll('a');
    spyOn(component, 'btnClick');
    list[1].querySelector('div button').click();
    expect(component.btnClick).toHaveBeenCalledWith(jasmine.any(Function));
  });
});
