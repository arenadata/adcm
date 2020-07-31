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
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { ClusterService } from '@app/core';
import { EventMessage, getMessage, SocketState } from '@app/core/store';
import { LogFile } from '@app/core/types';
import { MemoizedSelector } from '@ngrx/store';
import { MockStore, provideMockStore } from '@ngrx/store/testing';
import { of } from 'rxjs/internal/observable/of';

import { JobInfoComponent } from '../job-info.component';
import { ITimeInfo, LogComponent } from './log.component';
import { TextComponent } from './text.component';

const JobMock = { start_date: '', finish_date: '', status: '' };

describe('Job Module :: LogComponent', () => {
  let fixture: ComponentFixture<LogComponent>;
  let component: LogComponent;
  let store: MockStore;
  let messageSelector: MemoizedSelector<SocketState, EventMessage>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [MatIconModule],
      declarations: [LogComponent, JobInfoComponent, TextComponent],
      providers: [
        {
          provide: ClusterService,
          useValue: {
            getOperationTimeData: (): ITimeInfo => ({ start: '', end: '', time: '' }),
            Current: JobMock,
            getLog: () => of({ id: 1, name: 'log_test', type: 'stdout', content: 'First message' }),
          },
        },
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
    // component.socket$ = of({ event: 'add' });
    // fixture.detectChanges();
  });

  it('should be created', () => {
    expect(component).toBeTruthy();
  });

  it('content should updating', () => {
    component.currentLog = { id: 1, name: 'log_test', type: 'stdout', content: 'First message' } as LogFile;
    fixture.detectChanges();
    const text = fixture.nativeElement.querySelector('div.wrap app-log-text textarea');
    expect(text.innerHTML).toBe('First message');
    component.currentLog.content = 'Second message';
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('div.wrap app-log-text textarea').innerHTML).toBe('Second message');
  });
});
