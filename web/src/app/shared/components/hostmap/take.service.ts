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
import { Injectable } from '@angular/core';
import { ApiService } from '@app/core/api';
import { IActionParameter, Component } from '@app/core/types';
import { take, tap } from 'rxjs/operators';

import { CompTile, HostTile, IRawHosComponent, Post, StatePost, Stream, Tile } from './types';
import { FormGroup, ValidatorFn, AbstractControl, FormControl } from '@angular/forms';

@Injectable({
  providedIn: 'root'
})
export class TakeService {
  stream = new Stream();
  statePost = new StatePost();
  loadPost = new StatePost();
  sourceMap = new Map<string, Tile[]>([
    ['host', []],
    ['compo', []]
  ]);

  actionParameters: IActionParameter[];

  /**
   * Validation only
   */
  formGroup = new FormGroup({});

  //
  countConstraint = 0;

  constructor(private api: ApiService) {}

  get Hosts(): HostTile[] {
    return this.sourceMap.get('host');
  }

  get Components(): CompTile[] {
    return this.sourceMap.get('compo') as CompTile[];
  }

  initSource(url: string, actions: IActionParameter[]) {
    this.actionParameters = actions;
    this.sourceMap.set('host', []);
    this.sourceMap.set('compo', []);
    this.statePost.clear();
    this.formGroup = new FormGroup({});

    return this.api.get<IRawHosComponent>(url).pipe(
      tap(a => {
        this.setSource(a);
        if (a.hc) {
          this.statePost.update(a.hc);
          this.loadPost.update(a.hc);
          this.setRelations(a.hc);
          // this.checkConstraints();
        }
        this.formFill();
      })
    );
  }

  saveSource(cluster: { id: number; hostcomponent: string }) {
    const send = { cluster_id: cluster.id, hc: this.statePost.data };
    return this.api.post<Post[]>(cluster.hostcomponent, send).pipe(
      take(1),
      tap(data => {
        this.loadPost.update(data);
        this.statePost.update(data);
      })
    );
  }

  setSource(raw: IRawHosComponent) {
    const getActions = (c: Component) => {
      if (this.actionParameters) return this.actionParameters.filter(a => a.service === c.service_name && a.component === c.name).map(b => b.action);
    };

    if (raw.host) {
      const list = raw.host.map(h => new HostTile(h));
      this.sourceMap.set('host', [...list]);
    }

    if (raw.component) {
      const list = raw.component.map(c => new CompTile(c, getActions(c)));
      this.sourceMap.set('compo', [...this.sourceMap.get('compo'), ...list]);
    }
  }

  validateConstraints(a: CompTile): ValidatorFn {
    return (control: AbstractControl) => {
      console.log(a.limit, a.relations.length);
      if (a.limit && a.limit[0]) {
        if (a.limit[0] === '+' && a.relations.length < this.Hosts.length) return { 'Fucking constraints': a.name };
        else if (a.limit[0] > a.relations.length) return { 'Fucking constraints': a.name };
      }
      return null;
    };
  }

  formFill() {
    this.Components.map(a => {
      this.formGroup.addControl(`${a.service_id}/${a.id}`, new FormControl(a.relations.length, this.validateConstraints(a)));
    });
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

  clearAllRelations() {
    this.sourceMap.get('host').map(h => (h.relations = []));
    this.sourceMap.get('compo').map(s => (s.relations = []));
    this.formFill();
  }

  clearServiceFromHost(data: { rel: CompTile; model: HostTile }) {
    this.clear([data.model, data.rel]);
    this.statePost.delete(new Post(data.model.id, data.rel.service_id, data.rel.id));
    this.setFormValue(data.rel);
  }

  clearHostFromService(data: { rel: HostTile; model: CompTile }) {
    this.clear([data.rel, data.model]);
    this.statePost.delete(new Post(data.rel.id, data.model.service_id, data.model.id));
    this.setFormValue(data.model);
  }

  takeHost(host: HostTile) {
    this.stream.target = host;
    this.getLink('compo')
      .getSelected('host')
      .fork(this.handleLink, this.handleSelect);
  }

  takeComponent(component: CompTile) {
    this.stream.target = component;
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
    this.stream.selected = this.sourceMap.get(name).find(s => s.isSelected);
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
    // this.checkConstraints();

    this.setFormValue((isComp ? this.stream.target : this.stream.link) as CompTile);
  }

  setFormValue(c: CompTile) {
    const id = `${c.service_id}/${c.id}`;
    this.formGroup.controls[id].setValue(c.relations);
  }

  clear(tiles: Tile[]) {
    for (let a of tiles) {
      const name = a instanceof HostTile ? 'host' : 'compo';
      const link = this.sourceMap.get(name).find(h => h.id === a.id);
      const rel = tiles.find(b => b !== a);
      link.relations = link.relations.filter(r => r.id !== rel.id);
      a.isLink = false;
    }
    // this.checkConstraints();
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

  // checkConstraints() {
  //   this.countConstraint = this.sourceMap.get('compo').reduce((a, c) => {
  //     if (c.limit && c.limit[0]) {
  //       if (c.limit[0] === '+' && c.relations.length < this.sourceMap.get('host').length) a++;
  //       else if (c.limit[0] > c.relations.length) a++;
  //     }
  //     return a;
  //   }, 0);
  // }

  noLimit(comp: Tile) {
    if (comp.limit && Array.isArray(comp.limit) && comp.limit.length) {
      const a = comp.limit,
        b = a.length - 1,
        c = comp.relations.length;
      // if (a.includes('odd')) {
      //   //return comp.relations.length === 0 || comp.relations.length % 2 === 0;
      // }
      return a[b] === '+' || a[b] > c;
    } else return true;
  }

  cancel() {
    this.statePost.clear();
    this.statePost.update(this.loadPost.data);
    this.clearAllRelations();
    this.setRelations(this.loadPost.data);
    // this.checkConstraints();
    this.formFill();

    this.sourceMap.get('host').map(a => {
      a.isSelected = false;
      a.isLink = false;
    });
    this.sourceMap.get('compo').map(a => {
      a.isSelected = false;
      a.isLink = false;
    });
  }
}
