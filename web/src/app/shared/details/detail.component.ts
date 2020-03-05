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
import { Cluster, Host, IAction, Issue, Job, notIssue } from '@app/core/types';
import { Store } from '@ngrx/store';
import { Observable, of } from 'rxjs';
import { map, switchMap, tap, exhaustMap } from 'rxjs/operators';

import { SocketListenerDirective } from '../directives/socketListener.directive';
import { IDetails } from './details.service';

@Component({
  selector: 'app-detail',
  templateUrl: './detail.component.html',
  styleUrls: ['./detail.component.scss']
})
export class DetailComponent extends SocketListenerDirective implements OnInit, OnDestroy {
  request$: Observable<WorkerInstance>;
  isIssue: boolean;
  upgradable = false;
  actions: IAction[] = [];
  issues: Issue;
  status: number | string;

  current: IDetails;
  currentName = '';

  constructor(socket: Store<SocketState>, private route: ActivatedRoute, private service: ClusterService, private channel: ChannelService) {
    super(socket);
  }

  ngOnInit(): void {
    this.request$ = this.route.paramMap.pipe(
      switchMap(param => this.service.getContext(param)),
      tap(w => this.run(w))
    );

    super.startListenSocket();
  }

  ngOnDestroy(): void {
    this.service.clearWorker();
  }

  notIssue(issue: Issue) {
    return !notIssue(issue);
  }

  run(w: WorkerInstance) {
    const { id, name, typeName, actions, issue, status, prototype_name, prototype_display_name, prototype_version, bundle_id } = w.current;
    const { upgradable, upgrade } = w.current as Cluster;
    const { log_files, objects } = w.current as Job;
    const { provider_id } = w.current as Host;

    this.currentName = name;

    const parent = w.current.typeName === 'cluster' ? null : w.cluster;

    this.actions = actions;
    this.upgradable = upgradable;
    this.issues = issue;
    this.status = status;

    this.isIssue = this.notIssue(parent ? parent.issue : issue);

    this.current = {
      parent,
      id,
      name,
      typeName,
      actions,
      issue,
      upgradable,
      upgrade,
      status,
      log_files,
      objects,
      prototype_name,
      prototype_display_name,
      prototype_version,
      provider_id,
      bundle_id
    };
  }

  scroll(stop: { direct: -1 | 1 | 0; screenTop: number }) {
    this.channel.next('scroll', stop);
  }

  reset() {
    this.request$ = this.service.reset().pipe(
      this.takeUntil(),
      tap(a => this.run(a)),
      tap(_ => console.log('GET ::', this.current))
    );
  }

  socketListener(m: EventMessage) {
    if ((m.event === 'create' || m.event === 'delete') && m.object.type === 'bundle') {
      this.reset();
      return;
    }

    if (this.service.Current && this.service.Current.typeName === m.object.type && this.service.Current.id === m.object.id) {
      if (m.event === 'change_job_status' && this.service.Current.typeName === 'job') {
        this.reset();
        return;
      }

      if (m.event === 'change_state' || m.event === 'upgrade' || m.event === 'raise_issue') {
        this.reset();
        return;
      }

      if (m.event === 'clear_issue' && m.object.type === 'cluster') this.issues = {} as Issue;

      if (m.event === 'change_status') this.status = +m.object.details.value;
    }

    if (this.service.Cluster && m.event === 'clear_issue' && m.object.type === 'cluster' && this.service.Current.typeName !== 'cluster' && this.service.Cluster.id === m.object.id)
      this.issues = {} as Issue;

    this.isIssue = this.notIssue(this.issues);
  }
}
