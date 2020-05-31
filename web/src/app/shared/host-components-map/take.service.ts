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
import { FormControl, FormGroup, ValidationErrors } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { ApiService } from '@app/core/api';
import { IActionParameter, IRequires } from '@app/core/types';
import { filter, switchMap, take, tap, map } from 'rxjs/operators';

import { AddService } from '../add-component/add.service';
import { DialogComponent } from '../components';
import { DependenciesComponent } from './dependencies.component';
import { CompTile, Constraint, HostTile, IRawHosComponent, IStream, Post, StatePost, Tile } from './types';

@Injectable()
export class TakeService {
  stream = {} as IStream;
  statePost = new StatePost();
  loadPost = new StatePost();
  sourceMap = new Map<string, Tile[]>([
    ['host', []],
    ['compo', []],
  ]);

  actionParameters: IActionParameter[];
  formGroup = new FormGroup({});

  constructor(private api: ApiService, private dialog: MatDialog, private add: AddService) {}

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

  initSource(url: string, actions: IActionParameter[]) {
    this.actionParameters = actions;
    this.Hosts = [];
    this.Components = [];
    this.statePost.clear();
    this.loadPost.clear();
    this.formGroup = new FormGroup({});

    return this.api.get<IRawHosComponent>(url).pipe(
      tap((a) => {
        this.setSource(a);
        if (a.hc) {
          this.statePost.update(a.hc);
          this.loadPost.update(a.hc);
          this.setRelations(a.hc);
          this.checkEmptyHost();
        }
        this.formFill();
      })
    );
  }

  setSource(raw: IRawHosComponent) {
    if (raw.host) {
      const list = raw.host.map((h) => new HostTile(h));
      this.Hosts = [...list];
    }

    if (raw.component) {
      const list = raw.component.map(
        (c) => new CompTile(c, this.actionParameters ? this.actionParameters.filter((a) => a.service === c.service_name && a.component === c.name).map((b) => b.action) : null)
      );
      this.Components = [...this.Components, ...list];
    }
  }

  checkEmptyHost() {
    const ap = this.actionParameters;
    if (ap) {
      const isShrink = ap.every((a) => a.action === 'remove');
      const isExpand = ap.every((a) => a.action === 'add');
      const condition = (b: CompTile) => (a: IActionParameter) => b.component === `${a.service}/${a.component}`;
      const existCondition = (rel: CompTile[]) => (isShrink ? ap.some((a) => rel.some((b) => condition(b)(a))) : ap.every((a) => rel.some((b) => condition(b)(a))));
      this.Hosts = this.Hosts.map((a) => ({ ...a, disabled: existCondition(a.relations as CompTile[]) ? isExpand : isShrink }));
    }
  }

  setRelations(a: Post[]) {
    a.forEach((p) => {
      const host = this.Hosts.find((h) => h.id === p.host_id),
        service = this.Components.find((s) => s.id === p.component_id);
      if (host && service) {
        if (this.actionParameters) {
          service.relations = [...service.relations, host];
          const clone = { ...service };
          clone.disabled = service.actions.every((k) => k !== 'remove');
          host.relations = [...host.relations, clone];
        } else {
          host.relations = [...host.relations, service];
          service.relations = [...service.relations, host];
        }
      }
    });
  }

  /**
  https://docs.arenadata.io/adcm/sdk/config.html#components
  [1] – exactly once component shoud be installed;
  [0,1] – one or zero component shoud be installed;
  [1,2] – one or two component shoud be installed;
  [0,+] – zero or any more component shoud be installed (default value);
  [1,odd] – one or more component shoud be installed; total amount should be odd
  [0,odd] – zero or more component shoud be installed; if more than zero, total amount should be odd
  [odd] – the same as [1,odd]
  [1,+] – one or any more component shoud be installed;
  [+] – component shoud be installed on all hosts of cluster.
 */
  validateConstraints(cti: CompTile) {
    const oneConstraint = (a: Constraint, ins: number) => {
      switch (a[0]) {
        case 0:
          return null;
        case '+':
          return ins < this.Hosts.length ? 'Component should be installed on all hosts of cluster.' : null;
        case 'odd':
          return ins % 2 ? null : 'One or more component should be installed. Total amount should be odd.';
        default:
          return ins !== a[0] ? `Exactly ${a[0]} component should be installed` : null;
      }
    };
    const twoConstraint = (a: Constraint, ins: number) => {
      switch (a[1]) {
        case 'odd':
          return ins % 2 && ins >= a[0] ? null : a[0] === 0 ? 'Total amount should be odd.' : `Must be installed at least ${a[0]} components. Total amount should be odd.`;
        case '+':
        default:
          return ins < a[0] ? `Must be installed at least ${a[0]} components.` : null;
      }
    };
    const limitLength = (length: number) => (length === 1 ? oneConstraint : twoConstraint);
    return (): ValidationErrors => {
      const limit = cti.limit;
      if (limit) {
        const error = limitLength(limit.length)(limit, cti.relations.length);
        return error ? { error } : null;
      }
      return null;
    };
  }

  formFill() {
    this.Components.map((a) => this.formGroup.addControl(`${a.service_id}/${a.id}`, new FormControl(a.relations.length, this.validateConstraints(a))));
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
    this.getLink(this.Components).getSelected(this.Hosts).next(host);
  }

  takeComponent(component: CompTile) {
    this.getLink(this.Hosts).getSelected(this.Components).next(component);
  }

  getLink(source: Tile[]) {
    this.stream.linkSource = source;
    this.stream.link = this.stream.linkSource.find((s) => s.isSelected);
    this.stream.linkSource.forEach((s) => (s.isLink = false));
    return this;
  }

  getSelected(source: Tile[]) {
    this.stream.selected = source.find((s) => s.isSelected);
    if (this.stream.selected) this.stream.selected.isSelected = false;
    return this;
  }

  next(target: Tile) {
    if (this.stream.link) this.handleLink(this.stream.link, target);
    else if (this.stream.selected !== target) {
      target.isSelected = true;
      target.relations.forEach((e) => (this.stream.linkSource.find((s) => s.name === e.name && s.id === e.id).isLink = true));
    }
  }

  handleLink(link: Tile, target: Tile) {
    const isComp = target instanceof CompTile;
    const Component = (isComp ? target : link) as CompTile;
    const Host = isComp ? link : target;
    const post = new Post(Host.id, Component.service_id, Component.id);

    const checkActions = (host_id: number, com: CompTile, action: 'add' | 'remove'): boolean => {
      if (com.actions?.length) {
        const flag = this.loadPost.data.some((a) => a.component_id === com.id && a.service_id === com.service_id && a.host_id === host_id);
        if (action === 'remove') return flag ? com.actions.some((a) => a === 'remove') : true;
        if (action === 'add') return flag ? true : com.actions.some((a) => a === 'add');
      } else return true;
    };

    const noLimit = (c: Constraint, r: number) => {
      const v = c[c.length - 1];
      return v === '+' || v === 'odd' || v > r;
    };

    if (link.relations.find((e) => e.id === target.id)) {
      if (!checkActions(Host.id, Component, 'remove')) return;
      this.clear([target, link]);
      this.statePost.delete(post);
    } else if (Component.limit && noLimit(Component.limit, Component.relations.length)) {
      if (!checkActions(Host.id, Component, 'add')) return;
      if (Component.requires?.length) {
        this.dialog4Requires(Component.requires);
        return;
      }
      link.relations.push(target);
      target.relations.push(link);
      target.isLink = true;
      this.statePost.add(post);
    }
    this.setFormValue(Component);
  }

  dialog4Requires(model: IRequires[]) {
    this.dialog
      .open(DialogComponent, {
        data: {
          title: 'This component cannot be installed without the following dependencies.',
          component: DependenciesComponent,
          model,
          controls: ['Install All', 'It is clear'],
        },
      })
      .beforeClosed()
      .pipe(
        filter((a) => a),
        map((_) => model.map(a => ({prototype_id: a.id}))), //.reduce((p, c) =>  p = [...c.components.map(b => ({ prototype_id: b.id }))], [])),
        switchMap((result) => this.add.addService(result))
      )
      .subscribe();
  }

  setFormValue(c: CompTile) {
    this.formGroup.controls[`${c.service_id}/${c.id}`].setValue(c.relations);
  }

  saveSource(cluster_id: number, hostcomponent: string) {
    const send = { cluster_id, hc: this.statePost.data };
    return this.api.post<Post[]>(hostcomponent, send).pipe(
      take(1),
      tap((data) => {
        this.loadPost.update(data);
        this.statePost.update(data);
      })
    );
  }

  clear(tiles: Tile[]) {
    for (let a of tiles) {
      const name = a instanceof HostTile ? 'host' : 'compo';
      const link = this.sourceMap.get(name).find((h) => h.id === a.id);
      const rel = tiles.find((b) => b !== a);
      link.relations = link.relations.filter((r) => r.id !== rel.id);
      a.isLink = false;
    }
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

    this.setRelations(this.loadPost.data);
    this.formFill();
  }
}
