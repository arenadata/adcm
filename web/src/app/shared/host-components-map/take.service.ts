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

  raw: IRawHosComponent;

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
    this.reset();
    return this.api.get<IRawHosComponent>(url).pipe(tap((a) => this.init(a)));
  }

  reset() {
    this.Hosts = [];
    this.Components = [];
    this.statePost.clear();
    this.loadPost.clear();
    this.formGroup = new FormGroup({});
  }

  init(a: IRawHosComponent) {
    this.setSource(a);
    if (a.hc) {
      this.statePost.update(a.hc);
      this.loadPost.update(a.hc);
      this.setRelations(a.hc);
      this.checkEmptyHost();
    }
    this.formFill();
  }

  setSource(raw: IRawHosComponent) {
    this.raw = raw;
    if (raw.host) {
      this.Hosts = raw.host.map((h) => new HostTile(h));
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

  formFill() {
    this.Components.map((a) => this.formGroup.addControl(`${a.service_id}/${a.id}`, new FormControl(a.relations.length, this.validateConstraints(a))));
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
  validateConstraints(component: CompTile) {
    const getError = (constraint: Constraint, relations: HostTile[]) => {
      const [a1, a2, a3] = constraint;
      const countRelations = relations.length;
      if (a3) {
        switch (a3) {
          case 'depend':
            return relations.some((a) => a.relations.some((b) => b.id === component.id)) ? null : 'Must be installed because it is a dependency of another component';
        }
      } else if (a2) {
        switch (a2) {
          case 'depend':
            return relations.some((a) => a.relations.some((b) => b.id === component.id)) ? null : 'Must be installed because it is a dependency of another component';
          case 'odd':
            return countRelations % 2 && countRelations >= a1
              ? null
              : a1 === 0
              ? 'Total amount should be odd.'
              : `Must be installed at least ${a1} components. Total amount should be odd.`;
          case '+':
          default:
            return countRelations < a1 ? `Must be installed at least ${a1} components.` : null;
        }
      } else {
        switch (a1) {
          case 0:
            return null;
          case 'depend':
            return relations.some((a) => a.relations.some((b) => b.id === component.id)) ? null : 'Must be installed because it is a dependency of another component';
          case '+':
            return countRelations < this.Hosts.length ? 'Component should be installed on all hosts of cluster.' : null;
          case 'odd':
            return countRelations % 2 ? null : 'One or more component should be installed. Total amount should be odd.';
          default:
            return countRelations !== a1 ? `Exactly ${a1} component should be installed` : null;
        }
      }
    };
    return (): ValidationErrors => {
      const { limit, relations } = component;
      if (limit) {
        const error = getError(limit, relations);
        return error ? { error } : null;
      }
      return null;
    };
  }

  clearServiceFromHost(data: { rel: CompTile; model: HostTile }) {
    this.clear([data.model, data.rel]);
    this.statePost.delete(new Post(data.model.id, data.rel.service_id, data.rel.id));
    this.clearDependencies(data.rel);
    this.setFormValue(data.rel);
  }

  clearHostFromService(data: { rel: HostTile; model: CompTile }) {
    this.clear([data.rel, data.model]);
    this.statePost.delete(new Post(data.rel.id, data.model.service_id, data.model.id));
    this.clearDependencies(data.model);
    this.setFormValue(data.model);
  }

  clearDependencies(comp: CompTile) {
    const getLimitsFromState = (prototype_id: number) => this.raw.component.find((b) => b.prototype_id === prototype_id).constraint;

    if (comp.requires?.length) {
      this.findDependencies(comp).map((a) => {
        a.limit = getLimitsFromState(a.prototype_id);
        // a.color = 'white';
        a.notification = '';
        return a;
      });
      this.statePost.data.map((a) => this.checkDependencies(this.Components.find((b) => b.id === a.component_id)));
      this.formGroup.reset();
      this.formFill();
    }
  }

  findDependencies(component: CompTile) {
    const r = component.requires?.reduce((p, c) => [...p, ...c.components.map((a) => ({ prototype_id: a.prototype_id }))], []) || [];
    return this.Components.filter((a) => r.some((b) => b.prototype_id === a.prototype_id));
  }

  checkDependencies(component: CompTile) {
    this.findDependencies(component).map((a) => {
      // a.color = 'yellow';
      a.limit = a.limit ? [...a.limit, 'depend'] : ['depend'];
      return a;
    });
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
      if (!c) return true;
      const v = c[c.length - 1];
      return v === '+' || v === 'odd' || v > r || v === 'depend';
    };

    if (link.relations.find((e) => e.id === target.id)) {
      if (!checkActions(Host.id, Component, 'remove')) return;
      this.clear([target, link]);
      this.statePost.delete(post);
      this.clearDependencies(Component);
    } else if (noLimit(Component.limit, Component.relations.length)) {
      if (!checkActions(Host.id, Component, 'add')) return;
      if (Component.requires?.length) {
        const requires = Component.requires.reduce((p, c) => (c.components.some((a) => this.Components.some((b) => b.prototype_id === a.prototype_id)) ? p : [...p, c]), []);
        if (requires.length) {
          this.dialog4Requires(requires);
          return;
        } else {
          this.checkDependencies(Component);
          this.formGroup.reset();
          this.formFill();
        }
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
        map((_) => model.map((a) => ({ prototype_id: a.prototype_id }))),
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
      const name = 'service_id' in a ? 'compo' : 'host';
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
