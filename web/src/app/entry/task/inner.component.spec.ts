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
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterTestingModule } from '@angular/router/testing';
import { Job } from '@app/core/types';

import { InnerComponent } from './inner.component';

describe('InnerComponent', () => {
  let component: InnerComponent;
  let fixture: ComponentFixture<InnerComponent>;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [MatTableModule, MatIconModule, MatTooltipModule, RouterTestingModule],
      declarations: [InnerComponent],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(InnerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('job should display as row', () => {
    component.dataSource = [{ status: 'created', display_name: 'job_test', id: 1, start_date: '2020-07-30T12:28:59.431072Z', finish_date: '2020-07-30T12:29:00.222917Z' }] as Job[];
    fixture.detectChanges();
    const rows = fixture.nativeElement.querySelectorAll('table tr');
    expect(rows.length).toBe(1);
  });

  it('changing job status should display the appropriate icon', () => {
    const getIcon = () => fixture.nativeElement.querySelector('table tr td:last-child mat-icon');
    component.dataSource = [{ status: 'created', display_name: 'job_test', id: 1, start_date: '2020-07-30T12:28:59.431072Z', finish_date: '2020-07-30T12:29:00.222917Z' }] as Job[];
    fixture.detectChanges();
    const last_icon = getIcon();
    expect(last_icon.innerText).toBe('watch_later');

    component.dataSource[0].status = 'running';
    fixture.detectChanges();
    const last_icon2 = getIcon();
    expect(last_icon2.innerText).toBe('autorenew');

    component.dataSource[0].status = 'success';
    fixture.detectChanges();
    const last_icon3 = getIcon();
    expect(last_icon3.innerText).toBe('done');

    component.dataSource[0].status = 'failed';
    fixture.detectChanges();
    const last_icon4 = getIcon();
    expect(last_icon4.innerText).toBe('error');

    component.dataSource[0].status = 'aborted';
    fixture.detectChanges();
    const last_icon5 = getIcon();
    expect(last_icon5.innerText).toBe('block');
  });

  it('job property should dislplay in the columns of row table', () => {
    component.dataSource = [{ status: 'created', display_name: 'job_test', id: 1, start_date: '2020-07-30T12:28:59.431072Z', finish_date: '2020-07-30T12:29:00.222917Z' }] as Job[];
    fixture.detectChanges();
    const tds = fixture.nativeElement.querySelectorAll('table tr td');
    expect<string>(tds[0].innerText).toBe('job_test');
    expect<string>(tds[1].innerText).toBeFalsy();
    expect<string>(tds[2].innerText).toBeFalsy();

    component.dataSource[0].status = 'running';
    fixture.detectChanges();
    expect<string>(tds[1].innerText).toBeTruthy(); //.toBe('Jul 30, 2020, 3:28:59 PM');

    component.dataSource[0].status = 'success';
    fixture.detectChanges();
    expect<string>(tds[1].innerText).toBeTruthy(); //.toBe('Jul 30, 2020, 3:28:59 PM');
    expect<string>(tds[2].innerText).toBeTruthy(); //.toBe('Jul 30, 2020, 3:29:00 PM');
  });
});
