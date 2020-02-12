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
import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ChannelService, ClusterService, WorkerInstance } from '@app/core';
import { EventMessage, SocketState } from '@app/core/store';
import { Entities, Host, Issue } from '@app/core/types';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';

import { SocketListener } from '../directives/base.directive';
import { IDetails } from './details.service';

@Component({
  selector: 'app-detail',
  templateUrl: './detail.component.html',
  styleUrls: ['./detail.component.scss']
})
export class DetailComponent extends SocketListener implements OnInit, OnDestroy {
  current: IDetails;
  request$: Observable<IDetails>;

  constructor(socket: Store<SocketState>, private route: ActivatedRoute, private service: ClusterService, private channel: ChannelService) {
    super(socket);
  }

  ngOnInit(): void {
    this.request$ = this.route.paramMap.pipe(
      switchMap(param => this.service.getContext(param)),
      map(w => this.run(w))
    );

    super.startListenSocket();
  }

  ngOnDestroy(): void {
    this.service.clearWorker();
  }

  run(w: WorkerInstance): IDetails {
    const { id, name, typeName, actions, issue, upgradable, status, log_files, objects, prototype_name, prototype_version, provider_id, bundle_id } = {
      ...w.current
    };
    const parent = w.current.typeName === 'cluster' ? null : w.cluster;
    this.current = {
      parent,
      id,
      name,
      typeName,
      actions,
      issue,
      upgradable,
      status,
      log_files,
      objects,
      prototype_name,
      prototype_version,
      provider_id,
      bundle_id
    };
    return this.current;
  }

  scroll(stop: { direct: -1 | 1 | 0; screenTop: number }) {
    this.channel.next('scroll', stop);
  }

  socketListener(m: EventMessage) {
    if (m.event === 'create' && m.object.type === 'bundle') {
      this.request$ = this.service.reset().pipe(map(a => this.run(a)));
    }

    if (this.service.Current && this.service.Current.typeName === m.object.type && this.service.Current.id === m.object.id) {
      if (m.event === 'change_job_status' && this.service.Current.typeName === 'job') {
        this.request$ = this.service.reset().pipe(map(a => this.run(a)));
      }

      if (m.event === 'change_state' || m.event === 'upgrade' || m.event === 'raise_issue') {
        this.service
          .reset()
          .pipe(map(a => this.run(a)))
          .subscribe(c => (this.current = { ...c }));
      }

      if (m.event === 'clear_issue') {
        if (m.object.type === 'cluster') this.service.Cluster.issue = {} as Issue;
        this.current = { ...this.current, issue: null };
      }

      if (m.event === 'change_status') this.current = { ...this.current, status: +m.object.details.value };
    }
    if (
      this.service.Cluster &&
      m.event === 'clear_issue' &&
      m.object.type === 'cluster' &&
      this.service.Current.typeName !== 'cluster' &&
      this.service.Cluster.id === m.object.id
    )
      this.current = { ...this.current, issue: null };
  }
}
