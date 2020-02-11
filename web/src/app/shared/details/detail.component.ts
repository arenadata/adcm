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
import { ChannelService, ClusterService } from '@app/core';
import { EventMessage, SocketState } from '@app/core/store';
import { Cluster, Entities, Host, IAction, Issue } from '@app/core/types';
import { Store } from '@ngrx/store';
import { Observable, of } from 'rxjs';
import { switchMap, tap } from 'rxjs/operators';

import { SocketListener } from '../directives/base.directive';
import { CrumbsItem, NavigationService } from './navigation.service';

@Component({
  selector: 'app-detail',
  templateUrl: './detail.component.html',
  styleUrls: ['./detail.component.scss'],
  providers: [NavigationService]
})
export class DetailComponent extends SocketListener implements OnInit, OnDestroy {
  actions$: Observable<IAction[]> = of([]);
  issue: Issue;
  crumbs: CrumbsItem[];

  current: Entities;
  cluster: Cluster;

  constructor(
    socket: Store<SocketState>,
    private route: ActivatedRoute,
    private service: ClusterService,
    private nav: NavigationService,
    private channel: ChannelService
  ) {
    super(socket);
  }

  ngOnInit(): void {
    this.route.paramMap
      .pipe(
        this.takeUntil(),
        switchMap(param => this.service.getContext(param))
      )
      .subscribe(w => {
        this.current = w.current;
        this.cluster = w.cluster;
        this.initValue(w.current);
      });

    super.startListenSocket();
  }

  ngOnDestroy(): void {
    this.service.clearWorker();
  }

  get isIssue() {
    return this.service.Current && this.service.Current.issue && !!Object.keys(this.service.Current.issue).length;
  }

  isUpgradable() {
    return this.service.Cluster && this.service.Cluster.upgradable;
  }

  getDisplayName() {
    return this.service.Current
      ? 'display_name' in this.service.Current
        ? this.service.Current.display_name || this.service.Current.name
        : (this.service.Current as Host).fqdn
      : '';
  }

  scroll(stop: { direct: -1 | 1 | 0; screenTop: number }) {
    this.channel.next('scroll', stop);
  }

  socketListener(m: EventMessage) {
    if (m.event === 'create' && m.object.type === 'bundle') {
      this.service.reset().subscribe(a => this.initValue(a.current, m));
    }

    if (this.service.Current && this.service.Current.typeName === m.object.type && this.service.Current.id === m.object.id) {
      if (m.event === 'change_job_status' && this.service.Current.typeName === 'job') {
        this.service.reset().subscribe(a => this.initValue(a.current, m));
      }

      if (m.event === 'change_state' || m.event === 'upgrade' || m.event === 'raise_issue') {
        this.service.reset().subscribe(a => this.initValue(a.current, m));
      }

      if (m.event === 'clear_issue') {
        if (m.object.type === 'cluster') this.service.Cluster.issue = {} as Issue;
        this.service.Current.issue = {} as Issue;
        this.updateView();
      }

      if (m.event === 'change_status') {
        this.service.Current.status = +m.object.details.value;
        this.updateView();
      }
    }
    if (
      this.service.Cluster &&
      m.event === 'clear_issue' &&
      m.object.type === 'cluster' &&
      this.service.Current.typeName !== 'cluster' &&
      this.service.Cluster.id === m.object.id
    ) {
      this.service.Cluster.issue = {} as Issue;
      this.updateView();
    }
  }

  initValue(a: Entities, m?: EventMessage) {
    this.actions$ = !a.actions || !a.actions.length ? this.service.getActions() : of(a.actions);
    this.updateView();
    //console.log(`GET: ${this.service.Current.typeName}`, a, m);
  }

  updateView() {
    this.crumbs = this.nav.getCrumbs({
      cluster: this.service.Cluster,
      current: this.service.Current
    });
  }
}
