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
import { FormGroup } from '@angular/forms';
import { ChannelService } from '@app/core';
import { EventMessage, IEMObject, SocketState } from '@app/core/store';
import { IActionParameter } from '@app/core/types';
import { Store } from '@ngrx/store';

import { SocketListenerDirective } from '../../directives/socketListener.directive';
import { TakeService } from '../take.service';
import { CompTile, HostTile, Post, IStream, StatePost, Tile, IRawHosComponent } from '../types';

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
export class ServiceHostComponent extends SocketListenerDirective implements OnInit {
  showSpinner = false;
  showPopup = false;
  notify = '';

  stream = {} as IStream;
  statePost = new StatePost();
  loadPost = new StatePost();
  sourceMap = new Map<string, Tile[]>([
    ['host', []],
    ['compo', []],
  ]);
  form = new FormGroup({});

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

  saveFlag = false;
  initFlag = false;

  scrollEventData: { direct: 1 | -1 | 0; scrollTop: number };

  get Hosts(): HostTile[] {
    return this.sourceMap.get('host');
  }

  set Hosts(v: HostTile[]) {
    this.sourceMap.set('host', v);
  }

  get Components(): CompTile[] {
    return this.sourceMap.get('compo') as CompTile[];
  }

  set Components(v: CompTile[]) {
    this.sourceMap.set('compo', v);
  }

  constructor(public service: TakeService, private channel: ChannelService, socket: Store<SocketState>) {
    super(socket);
  }

  public get noValid() {
    return /*!!this.service.countConstraint */ !this.form.valid || !this.statePost.data.length;
  }

  ngOnInit() {
    this.load();
    super.startListenSocket();

    this.channel
      .on('scroll')
      .pipe(this.takeUntil())
      .subscribe((e) => (this.scrollEventData = e));
  }

  socketListener(m: EventMessage) {
    const isCurrent = (type: string, id: number) => type === 'cluster' && id === this.cluster.id;
    if ((m.event === 'change_hostcomponentmap' || m.event === 'change_state') && isCurrent(m.object.type, m.object.id) && !this.saveFlag) {
      this.reset().load();
    }
    if ((m.event === 'add' || m.event === 'remove') && isCurrent(m.object.details.type, +m.object.details.value)) this.update(m);
  }

  reset() {
    this.Hosts = [];
    this.Components = [];
    this.statePost.clear();
    this.loadPost.clear();
    this.form = new FormGroup({});
    return this;
  }

  update(em: EventMessage) {
    if (em.event === 'add') this.add(em.object);
    if (em.event === 'remove') this.remove(em.object);
  }

  add(io: IEMObject) {
    if (io.type === 'host') {
      const { id } = io;
      this.Hosts = [...this.Hosts, new HostTile({ id, fqdn: 'name' })];
    }
  }

  remove(io: IEMObject) {
    if (io.type === 'host') {
      const { id } = io;
      this.Hosts = this.Hosts.filter((a) => a.id !== id);
    }
  }

  load() {
    if (this.cluster) {
      if (this.initFlag) return;
      this.initFlag = true;

      this.service
        .load(this.cluster.hostcomponent)
        .pipe(this.takeUntil())
        .subscribe((raw: IRawHosComponent) => this.init(raw));
    }
  }

  init(raw: IRawHosComponent) {
    if (raw.host) this.Hosts = raw.host.map((h) => new HostTile(h));

    if (raw.component) {
      const list = raw.component.map(
        (c) => new CompTile(c, this.actionParameters ? this.actionParameters.filter((a) => a.service === c.service_name && a.component === c.name).map((b) => b.action) : null)
      );
      this.Components = [...this.Components, ...list];
    }

    if (raw.hc) {
      this.initFlag = false;
      this.statePost.update(raw.hc);
      this.loadPost.update(raw.hc);
      this.service.setRelations(raw.hc, this.Components, this.Hosts, this.actionParameters);
      this.Hosts = this.actionParameters ? this.service.checkEmptyHost(this.Hosts, this.actionParameters) : this.Hosts;
    }
    this.service.formFill(this.Components, this.Hosts, this.form);
  }

  clearServiceFromHost(data: { rel: CompTile; model: HostTile }) {
    this.service.clearServiceFromHost(data, this.statePost);
  }

  clearHostFromService(data: { rel: HostTile; model: CompTile }) {
    this.service.clearHostFromService(data, this.statePost);
  }

  selectHost(host: HostTile) {
    this.service.takeHost(host, this.Components, this.Hosts, this.stream);
  }

  selectService(comp: CompTile) {
    this.service.takeComponent(comp, this.Components, this.Hosts, this.stream);
  }

  save() {
    this.saveFlag = true;
    const { id, hostcomponent } = this.cluster;
    this.service.save(id, hostcomponent, this.statePost.data).subscribe((data) => {
      this.loadPost.update(data);
      this.statePost.update(data);
      this.saveResult.emit(data);
      this.notify = 'Settings saved.';
      this.showPopup = true;
      setTimeout(() => (this.showPopup = false), 2000);
      this.saveFlag = false;
    });
  }

  restore() {
    this.statePost.clear();
    this.statePost.update(this.loadPost.data);

    this.Hosts.forEach((a) => {
      a.isSelected = false;
      a.isLink = false;
      a.relations = [];
    });
    this.Components.forEach((a) => {
      a.isSelected = false;
      a.isLink = false;
      a.relations = [];
    });

    this.service.setRelations(this.loadPost.data, this.Components, this.Hosts, this.actionParameters);
    this.service.formFill(this.Components, this.Hosts, this.form);
  }
}
