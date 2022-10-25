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
import { Directive, Injector, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, convertToParamMap, ParamMap } from '@angular/router';
import { Store } from '@ngrx/store';
import { Observable, Subscription } from 'rxjs';
import { switchMap, tap } from 'rxjs/operators';

import { ChannelService, keyChannelStrim } from '../core/services';
import { ClusterService, WorkerInstance } from '../core/services/cluster.service';
import { EventMessage, getNavigationPath, setPathOfRoute, SocketState } from '../core/store';
import { EmmitRow, Host, IAction, Job } from '../core/types';
import { SocketListenerDirective } from '@app/shared/directives';
import { IDetails } from '@app/models/details';
import { AdcmEntity } from '../models/entity';
import { IIssues } from '../models/issue';
import { IssueHelper } from '../helpers/issue-helper';
import { ICluster } from '../models/cluster';

@Directive({
  selector: '[appBaseDetailAbstract]',
})
export abstract class BaseDetailAbstractDirective extends SocketListenerDirective implements OnInit, OnDestroy {
  subscription$: Subscription;
  upgradable = false;
  actions: IAction[] = [];
  status: number | string;
  issue: IIssues;
  current: IDetails;
  currentName = '';

  navigationPath: Observable<AdcmEntity[]> = this.store.select(getNavigationPath).pipe(this.takeUntil());

  constructor(
    socket: Store<SocketState>,
    protected route: ActivatedRoute,
    protected service: ClusterService,
    protected channel: ChannelService,
    protected store: Store,
    injector: Injector,
  ) {
    super(socket);
  }

  get Current() {
    return this.service.Current;
  }

  initContext(param: ParamMap): Observable<WorkerInstance> {
    return this.service.getContext(param);
  }

  ngOnInit(): void {
    this.subscription$ = this.route.paramMap.pipe(
      switchMap((param) => this.initContext(param)),
      tap((w) => this.run(w)),
      this.takeUntil(),
    ).subscribe();

    super.startListenSocket();
  }

  ngOnDestroy(): void {
    this.service.clearWorker();
  }

  get isIssue() {
    return IssueHelper.isIssue(this.issue);
  }

  run(w: WorkerInstance) {
    const {
      id,
      name,
      typeName,
      action,
      actions,
      issue,
      status,
      prototype_name,
      prototype_display_name,
      prototype_version,
      bundle_id,
      state,
    } = w.current;
    const { upgradable, upgrade, hostcomponent } = w.current as ICluster;
    const { log_files, objects } = w.current as Job;
    const { provider_id, provider_name } = w.current as Host;

    this.currentName = name;
    this.actions = actions;
    this.upgradable = upgradable;
    this.status = status;

    const parent = w.current.typeName === 'cluster' ? null : w.cluster;
    this.issue = issue;

    this.current = {
      parent,
      id,
      name,
      typeName,
      actions,
      action,
      issue,
      upgradable,
      upgrade,
      status,
      state,
      log_files,
      objects,
      prototype_name,
      prototype_display_name,
      prototype_version,
      provider_id,
      provider_name,
      bundle_id,
      hostcomponent,
    };
  }

  scroll(stop: { direct: -1 | 1 | 0; screenTop: number }) {
    this.channel.next(keyChannelStrim.scroll, stop);
  }

  reset() {
    if (this.subscription$) {
      this.subscription$.unsubscribe();
    }
    this.subscription$ = this.service.reset().pipe(
      this.takeUntil(),
      tap((a) => this.run(a)),
      this.takeUntil(),
    ).subscribe();
  }

  socketListener(m: EventMessage) {
    if ((m.event === 'create' || m.event === 'delete') && m.object.type === 'bundle') {
      this.reset();
      return;
    }

    const type = m.object.type === 'component' ? 'servicecomponent' : m.object.type;
    if (this.Current?.typeName === type && this.Current?.id === m.object.id) {
      if (this.service.Current.typeName === 'job' && (m.event === 'change_job_status' || m.event === 'add_job_log')) {
        this.reset();
        return;
      }

      if (m.event === 'change_state' || m.event === 'upgrade') {
        this.reset();
        return;
      }

      if (m.event === 'change_status') this.status = +m.object.details.value;
    }

  }

  refresh(event: EmmitRow): void {
    const { row } = event;

    const params: ParamMap = convertToParamMap({ cluster: row.id });
    this.store.dispatch(setPathOfRoute({ params }));

  }
}
