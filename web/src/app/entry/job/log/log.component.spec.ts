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
import { MatIconModule } from '@angular/material/icon';
import { ActivatedRoute, convertToParamMap, ParamMap } from '@angular/router';
import { ClusterService } from '@app/core';
import { EventMessage, getMessage, SocketState } from '@app/core/store';
import { Job, LogFile } from '@app/core/types';
import { MemoizedSelector } from '@ngrx/store';
import { MockStore, provideMockStore } from '@ngrx/store/testing';
import { of } from 'rxjs/internal/observable/of';

import { JobInfoComponent } from '../job-info.component';
import { LogComponent } from './log.component';
import { TextComponent } from './text.component';
import { ApiService } from '@app/core/api';

const LogMock = { id: 1, name: 'log_test', type: 'stdout', content: 'First message' } as LogFile;
const JobMock = { id: 1, start_date: '2020-08-03T11:56:16.191363Z', finish_date: null, status: 'running', log_files: [LogMock] } as Job;

describe('Job Module :: LogComponent', () => {
  let fixture: ComponentFixture<LogComponent>;
  let component: LogComponent;
  let service: ClusterService; // = new ClusterService({} as ApiService);
  let store: MockStore;
  let messageSelector: MemoizedSelector<SocketState, EventMessage>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [MatIconModule],
      declarations: [LogComponent, JobInfoComponent, TextComponent],
      providers: [
        { provide: ApiService, useValue: { getOne: () => of(JobMock), get: () => of(LogMock) } },
        { provide: ActivatedRoute, useValue: { params: of({ log: 1 }), paramMap: of(convertToParamMap({ log: 1 })) } },
        provideMockStore(),
      ],
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(LogComponent);
    store = TestBed.inject(MockStore);
    messageSelector = store.overrideSelector(getMessage, { event: 'change_status' });
    component = fixture.componentInstance;
    service = TestBed.inject(ClusterService);
    //service.getContext = () => of({ current: JobMock, cluster: null });
    // component.socket$ = of({ event: 'add' });
    //fixture.detectChanges();
  });

  it('should be created', () => {
    expect(component).toBeTruthy();
  });

  it('content in the text-log should updating', () => {
    //const serviceSpy = spyOn(service, 'getContext');
    //serviceSpy.and.callFake(() => of({ current: JobMock, cluster: null }));
    service.getContext(convertToParamMap({ job: 1 })).subscribe();

    component.currentLog = LogMock;
    fixture.detectChanges();
    const text = fixture.nativeElement.querySelector('div.wrap app-log-text textarea');
    expect(text.innerHTML).toBe('First message');
    component.currentLog.content = 'Second message';
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('div.wrap app-log-text textarea').innerHTML).toBe('Second message');
  });

  it('if job status === running job-info should display start date and autorenew icon', () => {
    service.getContext(convertToParamMap({ job: 1 })).subscribe(_ => {
      component.currentLog = LogMock;
      fixture.detectChanges();
      const info = fixture.nativeElement.querySelector('app-job-info div.time-info');
      const start = info.querySelectorAll('div')[0].querySelector('span');
      const sd = new Date(Date.parse(JobMock.start_date));
      expect(start.innerText).toBe(sd.toLocaleTimeString());
    });
    
    
  });
});
