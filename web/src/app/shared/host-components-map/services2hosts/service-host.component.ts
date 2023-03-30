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
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { ChannelService } from '@app/core/services';
import { keyChannelStrim } from '@app/core/services';
import { EventMessage, IEMObject, SocketState } from '@app/core/store';
import { IActionParameter } from '@app/core/types';
import { Store } from '@ngrx/store';
import { SocketListenerDirective } from '@app/shared/directives';
import { getSelected, TakeService } from '../take.service';
import { CompTile, HostTile, IRawHosComponent, Post, StatePost, Tile } from '../types';
import { ApiService } from "@app/core/api";
import { Observable } from "rxjs";

@Component({
  selector: 'app-service-host',
  templateUrl: './service-host.component.html',
  styleUrls: ['./service-host.component.scss'],
})
export class ServiceHostComponent extends SocketListenerDirective implements OnInit {
  showSpinner = false;

  statePost = new StatePost();
  loadPost = new StatePost();
  sourceMap = new Map<string, Tile[]>([
    ['host', []],
    ['compo', []],
  ]);

  form = new FormGroup({});

  @Input()
  cluster: { id: number; hostcomponent: string | IRawHosComponent };

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

  get selectedComponent() {
    return this.Components.find((component) => component.isSelected);
  }

  constructor(public service: TakeService, private channel: ChannelService, socket: Store<SocketState>, private api: ApiService) {
    super(socket);
  }

  public get noValid() {
    return /*!!this.service.countConstraint */ !this.form.valid || !this.statePost.data.length;
  }

  ngOnInit() {
    this.load();
    super.startListenSocket();

    this.channel
      .on(keyChannelStrim.scroll)
      .pipe(this.takeUntil())
      .subscribe((e) => (this.scrollEventData = e));
  }

  getClusterInfo(): Observable<any> {
    return this.api.get(`api/v1/cluster/${this.cluster.id}/hostcomponent/`);
  }

  socketListener(m: EventMessage) {
    const isCurrent = (type: string, id: number) => type === 'cluster' && id === this.cluster?.id;
    if (
      (m.event === 'change_hostcomponentmap' || m.event === 'change_state') &&
      isCurrent(m.object.type, m.object?.id) &&
      !this.saveFlag
    ) {
      this.reset().load();
    }
    if ((m.event === 'add' || m.event === 'remove') && isCurrent(m.object.details.type, +m.object.details.value))
      this.update(m);
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
    const { id, type, details } = io;
    if (details.type === 'cluster' && +details.value === this.cluster?.id && typeof this.cluster.hostcomponent === 'string') {
      this.service
        .load(this.cluster.hostcomponent as string)
        .pipe(this.takeUntil())
        .subscribe((raw: IRawHosComponent) => {
          if (type === 'host')
            this.Hosts = [
              ...this.Hosts,
              ...this.service.fillHost(
                raw.host.map((h) => new HostTile(h)).filter((h) => h?.id === id),
                this.actionParameters
              ),
            ];
          if (type === 'service')
            this.Components = [
              ...this.Components,
              ...this.service.fillComponent(
                raw.component.filter((a) => a.service_id === id && this.Components.every((b) => b?.id !== a?.id)),
                this.actionParameters
              ),
            ];
        });
    } else if (typeof this.cluster.hostcomponent !== 'string') {
      this.getClusterInfo()
        .pipe(this.takeUntil())
        .subscribe((res) => {
          this.Hosts = [
            ...this.Hosts,
            ...this.service.fillHost(
              res.host.map((h) => new HostTile(h)).filter((h) => h?.id === id),
              this.actionParameters
            ),
          ];
        });
    }
  }

  /** host only */
  remove(io: IEMObject) {
    if (io.type === 'host') {
      const { id } = io;
      this.Hosts = this.Hosts.filter((a) => a?.id !== id);
    }
  }

  load() {
    if (this.cluster) {
      if (this.initFlag) return;
      this.initFlag = true;

      if (typeof this.cluster.hostcomponent === 'string' ) {
        this.service
          .load(this.cluster.hostcomponent)
          .pipe(this.takeUntil())
          .subscribe((raw: IRawHosComponent) => this.init(raw));
      } else {
        this.init(this.cluster.hostcomponent);
      }
    }
  }

  init(raw: IRawHosComponent) {
    if (raw?.host) this.Hosts = raw.host.map((h) => new HostTile(h));

    if (raw?.component)
      this.Components = [...this.Components, ...this.service.fillComponent(raw.component, this.actionParameters)];

    if (raw?.hc) {
      this.initFlag = false;
      this.statePost.update(raw.hc);
      this.loadPost.update(raw.hc);
      this.service.setRelations(raw.hc, this.Components, this.Hosts, this.actionParameters);
      this.service.fillHost(this.Hosts, this.actionParameters);
    }
    this.service.formFill(this.Components, this.Hosts, this.form);
  }

  clearServiceFromHost(data: { relation: CompTile; model: HostTile }) {
    this.service.divorce([data.relation, data.model], this.Components, this.Hosts, this.statePost, this.form);
  }

  clearHostFromService(data: { relation: HostTile; model: CompTile }) {
    this.service.divorce([data.model, data.relation], this.Components, this.Hosts, this.statePost, this.form);
  }

  selectHost(host: HostTile) {
    const stream = {
      linkSource: this.Components,
      link: getSelected(this.Components),
      selected: getSelected(this.Hosts),
    };
    this.service.next(host, stream, this.Components, this.Hosts, this.statePost, this.loadPost, this.form);
  }

  selectService(component: CompTile) {
    const stream = {
      linkSource: this.Hosts,
      link: getSelected(this.Hosts),
      selected: getSelected(this.Components),
    };
    this.service.next(component, stream, this.Components, this.Hosts, this.statePost, this.loadPost, this.form);
  }

  save() {
    this.saveFlag = true;
    const { id, hostcomponent } = this.cluster;
    this.service.save(id, hostcomponent, this.statePost.data).subscribe((data) => {
      this.loadPost.update(data);
      this.statePost.update(data);
      this.saveResult.emit(data);
      this.saveFlag = false;
      this.channel.next(keyChannelStrim.notifying, 'Successfully saved.');
    });
  }

  restore() {
    const ma = (a: Tile): void => {
      a.isSelected = false;
      a.isLink = false;
      a.relations = [];
    };

    this.Hosts.forEach(ma);
    this.Components.forEach(ma);

    this.statePost.clear();
    this.statePost.update(this.loadPost.data);

    this.service.setRelations(this.loadPost.data, this.Components, this.Hosts, this.actionParameters);
    this.form = new FormGroup({});
    this.service.formFill(this.Components, this.Hosts, this.form);
  }
}
