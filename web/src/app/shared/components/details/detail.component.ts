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
import { IAction, Entities, Issue } from '@app/core/types';
import { Store } from '@ngrx/store';
import { Observable, of } from 'rxjs';
import { switchMap, tap } from 'rxjs/operators';

import { SocketListener } from '../../directives/base.directive';
import { CrumbsItem, NavigationService } from './navigation.service';

@Component({
  selector: 'app-detail',
  templateUrl: './detail.component.html',
  styleUrls: ['./detail.component.scss'],
  providers: [NavigationService],
})
export class DetailComponent extends SocketListener implements OnInit, OnDestroy {
  actions$: Observable<IAction[]>;
  issue: Issue;
  crumbs: CrumbsItem[];
  leftMenu: any[];
  model$ = this.route.paramMap.pipe(switchMap(param => this.current.getContext(param).pipe(tap(w => this.initValue(w.current)))));

  constructor(
    socket: Store<SocketState>,
    private route: ActivatedRoute,
    private current: ClusterService,
    private nav: NavigationService,
    private channel: ChannelService
  ) {
    super(socket);
  }

  getParentLink(objects: { id: number; type: string }[], ind: number) {
    return objects.filter((a, i) => i <= ind).reduce((a, c) => [...a, c.type, c.id], ['/']);
  }

  scroll(stop: { direct: -1 | 1 | 0; screenTop: number }) {
    this.channel.next('scroll', stop);
  }

  ngOnInit(): void {
    super.startListenSocket();
  }

  socketListener(m: EventMessage) {
    if (this.current.Current && this.current.Current.typeName === m.object.type && this.current.Current.id === m.object.id) {
      
      if (m.event === 'change_job_status' && this.current.Current.typeName === 'job') {
        this.current.reset().subscribe(a => this.initValue(a, m));
      }
      
      if (m.event === 'change_state' || m.event === 'upgrade' || m.event === 'raise_issue') {
        this.current.reset().subscribe(a => this.initValue(a, m));
      }

      if (m.event === 'clear_issue') {
        if (m.object.type === 'cluster') this.current.Cluster.issue = {} as Issue;
        this.current.Current.issue = {} as Issue;
        this.updateView();
      }

      if (m.event === 'change_status') {
        this.current.Current.status = +m.object.details.value;
        this.updateView();
      }
    }
    if (
      this.current.Cluster &&
      m.event === 'clear_issue' &&
      m.object.type === 'cluster' &&
      this.current.Current.typeName !== 'cluster' &&
      this.current.Cluster.id === m.object.id
    ) {
      this.current.Cluster.issue = {} as Issue;
      this.updateView();
    }
  }

  initValue(a: Entities, m?: EventMessage) {
    this.actions$ = !a.actions || !a.actions.length ? this.current.getActions() : of(a.actions);
    this.updateView();
    console.log(`GET: ${this.current.Current.typeName}`, a, m);
  }

  updateView() {
    this.leftMenu = this.nav.getMenu(this.current.Current);
    this.crumbs = this.nav.getCrumbs({
      cluster: this.current.Cluster,
      current: this.current.Current,
    });
  }

  get isIssue() {
    return this.current.Current.issue && !!Object.keys(this.current.Current.issue).length;
  }
}
