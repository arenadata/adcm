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
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { ChannelService } from '@app/core';
import { ApiService } from '@app/core/api';
import { EventMessage, SocketState } from '@app/core/store';
import { Component as adcmComponent, Host, IActionParameter } from '@app/core/types';
import { Store } from '@ngrx/store';
import { Subject, throwError } from 'rxjs';
import { catchError, take, tap } from 'rxjs/operators';

import { SocketListener } from '../../../directives/base.directive';
import { CompTile, HostTile, Post, StatePost, Stream, Tile } from '../types';

@Component({
  selector: 'app-service-host',
  templateUrl: './service-host.component.html',
  styleUrls: ['./service-host.component.scss'],
  animations: [
    trigger('popup', [
      state('show', style({ opacity: 1 })),
      state('hide', style({ opacity: 0 })),
      transition('hide => show', [animate('.2s')]),
      transition('show => hide', [animate('2s')]),
    ]),
  ],
})
export class ServiceHostComponent extends SocketListener implements OnInit {
  countConstraint = 0;
  showSpinner = false;
  showPopup = false;
  all$ = new Subject<Tile[]>();

  @Input()
  cluster: { id: number; hostcomponent: string };

  /**
   * fixed position buttons for the scrolling
   */
  @Input()
  fixedButton = true;

  /**
   * hide Save button
   */
  @Input()
  hideButton = false;

  @Input()
  actionParameters: IActionParameter[];

  @Output() saveResult = new EventEmitter<Post[]>();

  statePost = new StatePost();
  loadPost = new StatePost();
  sourceMap = new Map<string, Tile[]>([['host', []], ['compo', []]]);
  stream = new Stream();

  saveFlag = false;
  initFlag = false;

  scrollEventData: { direct: 1 | -1 | 0 };

  constructor(private api: ApiService, private channel: ChannelService, socket: Store<SocketState>) {
    super(socket);
  }

  public get noValid() {
    return !!this.countConstraint || !this.statePost.data.length;
  }

  ngOnInit() {
    this.init();
    super.startListenSocket();

    this.channel
      .on('scroll')
      .pipe(this.takeUntil())
      .subscribe(e => (this.scrollEventData = e.value));
  }

  socketListener(m: EventMessage) {
    if (
      ((m.event === 'change_hostcomponentmap' || m.event === 'change_state') &&
        m.object.type === 'cluster' &&
        m.object.id === this.cluster.id &&
        !this.saveFlag) ||
      ((m.event === 'add' || m.event === 'remove') && m.object.details.type === 'cluster' && +m.object.details.value === this.cluster.id)
    ) {
      this.clearRelations();
      this.checkConstraints();
      this.init();
      this.initFlag = true;
    }
  }

  init() {
    if (this.initFlag) return;
    this.initFlag = true;

    this.sourceMap.set('host', []);
    this.sourceMap.set('compo', []);
    this.statePost.clear();

    const constraint = (c: number[] | string[]) => {
      if (c && c[0] && c[0] === '+') c = [this.sourceMap.get('host').length];
      return c;
    };

    const getActions = (c: adcmComponent) => {
      if (this.actionParameters) return this.actionParameters.filter(a => a.service === c.service_name && a.component === c.name).map(b => b.action);
    };

    this.api
      .get<{ component: adcmComponent[]; host: Host[]; hc: Post[] }>(this.cluster.hostcomponent)
      .pipe(
        tap(a => {
          if (a.host) this.sourceMap.set('host', a.host.map(h => new HostTile(h.id, h.fqdn)));
        }),
        tap(a => {
          if (a.component) {
            const list = a.component.map(
              c => new CompTile(c.id, c.service_id, c.display_name, constraint(c.constraint), c.service_state !== 'created', getActions(c)),
            );

            this.sourceMap.set('compo', [...this.sourceMap.get('compo'), ...list]);
          }
        }),
        tap((a: { component: adcmComponent[]; host: Host[]; hc: Post[] }) => {
          if (a.hc) {
            this.statePost.update(a.hc);
            this.loadPost.update(a.hc);
            this.setRelations(a.hc);
            this.checkConstraints();
            this.initFlag = false;
          }
        }),
        this.takeUntil(),
      )
      .subscribe();
  }

  setRelations(a: Post[]) {
    a.forEach(p => {
      const host = this.sourceMap.get('host').find(h => h.id === p.host_id),
        service = this.sourceMap.get('compo').find(s => s.id === p.component_id);
      if (host && service) {
        if (this.actionParameters) {
          service.relations = [...service.relations, host];
          const clone = { ...service };
          clone.disabled = service.actions.every(k => k !== 'remove');
          host.relations = [...host.relations, clone];
        } else {
          host.relations = [...host.relations, service];
          service.relations = [...service.relations, host];
        }
      }
    });
  }

  clearRelations() {
    this.sourceMap.get('host').map(h => (h.relations = []));
    this.sourceMap.get('compo').map(s => (s.relations = []));
  }

  checkConstraints() {
    this.countConstraint = this.sourceMap.get('compo').reduce((a, c) => {
      if (c.limit && c.limit[0]) {
        if (c.limit[0] === '+' && c.relations.length < this.sourceMap.get('host').length) a++;
        else if (c.limit[0] > c.relations.length) a++;
      }
      return a;
    }, 0);
  }

  clearServiceFromHost(data: { rel: CompTile; model: HostTile }) {
    this.clear([data.model, data.rel]);
    this.statePost.delete(new Post(data.model.id, data.rel.service_id, data.rel.id));
  }

  clearHostFromService(data: { rel: HostTile; model: CompTile }) {
    this.clear([data.rel, data.model]);
    this.statePost.delete(new Post(data.rel.id, data.model.service_id, data.model.id));
  }

  selectHost(host: HostTile) {
    this.stream.target = host;
    this.getLink('compo')
      .getSelected('host')
      .fork(this.handleLink, this.handleSelect);
  }

  selectService(comp: CompTile) {
    this.stream.target = comp;
    this.getLink('host')
      .getSelected('compo')
      .fork(this.handleLink, this.handleSelect);
  }

  getLink(name: string) {
    this.stream.linkSource = this.sourceMap.get(name);
    this.stream.link = this.stream.linkSource.find(s => s.isSelected);
    this.stream.linkSource.forEach(s => (s.isLink = false));
    return this;
  }

  getSelected(name: string) {
    this.stream.selected = this.sourceMap.get(name).find(_s => _s.isSelected);
    if (this.stream.selected) this.stream.selected.isSelected = false;
    return this;
  }

  fork(one: { (): void; (): void; call?: any }, two: { (): void; (): void; call?: any }) {
    if (this.stream.link) one.call(this);
    else if (this.stream.selected !== this.stream.target) two.call(this);
  }

  handleSelect() {
    this.stream.target.isSelected = true;
    this.stream.target.relations.forEach(e => (this.stream.linkSource.find(s => s.name === e.name && s.id === e.id).isLink = true));
  }

  checkActions(host: HostTile, com: CompTile, action: 'add' | 'remove'): boolean {
    const flag = this.loadPost.data.some(a => a.component_id === com.id && a.service_id === com.service_id && a.host_id === host.id);
    if (com.actions && com.actions.length) {
      if (action === 'remove') {
        if (flag) return com.actions.some(a => a === 'remove');
        else return true;
      }
      if (action === 'add') {
        if (flag) return true;
        else return com.actions.some(a => a === 'add');
      }
    } else return true;
  }

  handleLink() {
    const str = this.stream;
    const isComp = this.stream.target instanceof CompTile;
    const CurrentServiceComponent = (isComp ? this.stream.target : this.stream.link) as CompTile,
      CurrentHost = isComp ? this.stream.link : this.stream.target;
    const post = new Post(CurrentHost.id, CurrentServiceComponent.service_id, CurrentServiceComponent.id);

    if (str.link.relations.find(e => e.id === str.target.id)) {
      if (!this.checkActions(CurrentHost, CurrentServiceComponent, 'remove')) return;
      this.clear([str.target, str.link]);
      this.statePost.delete(post);
    } else if (this.noLimit(CurrentServiceComponent)) {
      if (!this.checkActions(CurrentHost, CurrentServiceComponent, 'add')) return;
      str.link.relations.push(str.target);
      str.target.relations.push(str.link);
      str.target.isLink = true;
      this.statePost.add(post);
    }
    this.checkConstraints();
  }

  clear(tiles: Tile[]) {
    for (let a of tiles) {
      const name = a instanceof HostTile ? 'host' : 'compo';
      const link = this.sourceMap.get(name).find(h => h.id === a.id);
      const rel = tiles.find(b => b !== a);
      link.relations = link.relations.filter(r => r.id !== rel.id);
      a.isLink = false;
    }
    this.checkConstraints();
  }

  save() {
    const send = { cluster_id: this.cluster.id, hc: this.statePost.data };
    this.saveFlag = true;
    this.api
      .post<Post[]>(this.cluster.hostcomponent, send)
      .pipe(
        take(1),
        catchError(e => {
          this.showPopup = false;
          return throwError(e);
        }),
      )
      .subscribe(data => {
        this.loadPost.update(data);
        this.statePost.update(data);
        this.saveResult.emit(data);
        this.showPopup = true;
        setTimeout(() => (this.showPopup = false), 2000);
        this.saveFlag = false;
      });
  }

  cancel() {
    this.statePost.clear();
    this.statePost.update(this.loadPost.data);
    this.clearRelations();
    this.setRelations(this.loadPost.data);
    this.checkConstraints();
    this.sourceMap.get('host').map(a => {
      a.isSelected = false;
      a.isLink = false;
    });
    this.sourceMap.get('compo').map(a => {
      a.isSelected = false;
      a.isLink = false;
    });
  }

  noLimit(comp: Tile) {
    if (comp.limit && Array.isArray(comp.limit) && comp.limit.length) {
      const a = comp.limit,
        b = a.length - 1,
        c = comp.relations.length;
      return a[b] === '+' || a[b] > c;
    } else return true;
  }
}
