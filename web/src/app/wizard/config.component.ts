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
import { animate, state, style, transition, trigger } from '@angular/animations';
import { Store } from '@ngrx/store';
import { combineLatest, Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { Component, Input, OnInit } from '@angular/core';

import { ClusterService } from '@app/core/services/cluster.service';
import { ApiService } from '@app/core/api';
import { SocketState } from '@app/core/store';
import { Cluster, Entities, Host, Issue, Provider, Service } from '@app/core/types';
import { BaseDirective } from '@app/shared/directives/base.directive';

@Component({
  selector: 'app-wizard-config',
  animations: [
    trigger('showForm', [
      state('show', style({ width: '95vh', height: '95ch' })),
      state('hide', style({ width: 0, height: 0 })),
      transition('show<=>hide', animate('.3s ease-in')),
    ]),
  ],
  templateUrl: './config.component.html',
  styleUrls: ['./config.component.scss'],
})
export class ConfigComponent extends BaseDirective implements OnInit {
  hosts$: Observable<any[]>;
  services$: Observable<Service[]>;
  pro$: Observable<Provider[]>;
  isShowForm = false;
  current: Entities;

  @Input() cluster: Cluster;

  constructor(private api: ApiService, private socket: Store<SocketState>, private cs: ClusterService) {
    super();
  }

  ngOnInit() {
    this.onLoad();

    // this.socket
    //   .pipe(
    //     select(getMessage),
    //     filter((m: EventMessage) => !!m && !!m.event && !!this.cs.Current),
    //     takeUntil(this.destroy$)
    //   )
    //   .subscribe(m => this.reflect(m));
  }

  // reflect(m: EventMessage) {}

  onLoad() {
    this.hosts$ = combineLatest([this.api.getPure<Provider>('provider'), this.api.get<Host[]>(this.cluster.host)]).pipe(
      map(a => {
        const [p, hosts] = a;
        return p.map(c => ({ ...c, hosts: hosts.filter(h => h.provider_id === c.id) }));
      })
    );

    this.services$ = this.api.get<Service[]>(this.cluster.service);
  }

  show(type: string, item: Entities) {
    this.current = { type, ...item };
    this.isShowForm = true;
  }

  checkIssue(issue: Issue): boolean {
    return issue && issue.hasOwnProperty('config') && !issue.config;
  }
}
