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
import { Component, OnInit, ViewChild } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { MatSlider } from '@angular/material/slider';
import { ApiService } from '@app/core/api';
import { EventMessage, getMessage, State } from '@app/core/store';
import { select, Store } from '@ngrx/store';
import { BehaviorSubject, Subject } from 'rxjs';
import { filter, takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-log',
  templateUrl: './log.component.html',
  styleUrls: ['./log.component.scss'],
})
export class LogComponent implements OnInit {
  destroy$ = new Subject();

  typeName: string;
  eventName: string;

  form = new FormGroup({
    typesName: new FormControl('cluster'),
    eventsName: new FormControl('change_state'),
    timeOut: new FormControl(false),
  });

  logs$ = new BehaviorSubject<{ event: EventMessage; response: any }[]>([]);

  events = [
    'all',
    'change_state',
    'add',
    'create',
    'delete',
    'remove',
    'change_config',
    'change_status',
    'change_job_status',
    'change_hostcomponentmap',
    'raise_issue',
    'clear_issue',
    'upgrade',
  ];

  types = ['all', 'job', 'task', 'cluster', 'host', 'service'];

  @ViewChild('slider') slider: MatSlider;

  constructor(private store: Store<State>, private api: ApiService) {
    // this.store.dispatch(socketInit());
  }

  ngOnInit() {
    this.store
      .pipe(
        select(getMessage),
        filter((m: EventMessage) => !!m && !!m.event),
        takeUntil(this.destroy$)
      )
      .subscribe(m => this.reflect(m));
  }

  reflect(m: EventMessage) {
    const typeName = this.form.get('typesName').value,
      eventName = this.form.get('eventsName').value;
    if ((m.object.type === typeName || typeName === 'all') && (m.event === eventName || eventName === 'all')) {
      if (this.form.get('timeOut').value)
        setTimeout(
          () => this.api.getOne<any>(m.object.type, m.object.id).subscribe(value => this.list(m, value)),
          this.slider.value
        );
      else this.api.getOne<any>(m.object.type, m.object.id).subscribe(value => this.list(m, value));
    } 
    // else this.list(m, `Not request for ${eventName} event.`);
  }

  list(m: EventMessage, value: any) {
    const { type, id } = m.object;
    const list = [
      ...this.logs$.getValue(),
      {
        event: m,
        response: { title: `Request for [ /api/v1/${type}/${id}/ ]`, value },
      },
    ];
    this.logs$.next(list.reverse());
  }

  refresh() {
    this.logs$.next([]);
  }
}
