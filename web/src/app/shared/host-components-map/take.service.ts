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
import { Component, Host, IActionParameter, IRequires } from '@app/core/types';
import { filter, map, switchMap, take } from 'rxjs/operators';

import { AddService } from '../add-component/add.service';
import { DialogComponent } from '../components';
import { DependenciesComponent } from './dependencies.component';
import { CompTile, Constraint, HostTile, IRawHosComponent, IStream, Post, StatePost, Tile } from './types';

export const getSelected = (from: Tile[]) => from.find((a) => a.isSelected);

@Injectable()
export class TakeService {
  /**
   * Object for saving state on user click
   *
   * @memberof TakeService
   */
  stream = {} as IStream;

  constructor(private api: ApiService, private dialog: MatDialog, private add: AddService) {}

  //#region ----- HttpClient ------
  load(url: string) {
    return this.api.get<IRawHosComponent>(url);
  }

  save(cluster_id: number, hostcomponent: string, hc: Post[]) {
    const send = { cluster_id, hc };
    return this.api.post<Post[]>(hostcomponent, send).pipe(take(1));
  }
  //#endregion

  //#region after a successful download, run and fill in
  fillHost(ph: Partial<Host>[], ap: IActionParameter[]) {
    const isShrink = () => ap.every((a) => a.action === 'remove');
    const isExpand = () => ap.every((a) => a.action === 'add');
    const condition = (b: CompTile) => (a: IActionParameter) => b.component === `${a.service}/${a.component}`;
    const existCondition = (rel: CompTile[]) =>
      isShrink() ? ap.some((a) => rel.some((b) => condition(b)(a))) : ap.every((a) => rel.some((b) => condition(b)(a)));
    const checkEmptyHost = (h: HostTile) => (existCondition(h.relations as CompTile[]) ? isExpand() : isShrink());
    return ph.map((h) => new HostTile(h)).map((h) => ({ ...h, disabled: !ap ? false : checkEmptyHost(h) }));
  }

  fillComponent(pc: Component[], ap: IActionParameter[]) {
    return pc.map(
      (c) =>
        new CompTile(
          c,
          ap ? ap.filter((a) => a.service === c.service_name && a.component === c.name).map((b) => b.action) : null
        )
    );
  }

  setRelations(rel: Post[], cs: CompTile[], hs: HostTile[], ap: IActionParameter[]) {
    rel.forEach((p) => {
      const host = hs.find((h) => h.id === p.host_id),
        component = cs.find((s) => s.id === p.component_id);
      if (host && component) {
        if (ap) {
          component.relations = [...component.relations, host];
          const clone_component = { ...component };
          clone_component.disabled = component.actions.every((k) => k !== 'remove');
          host.relations = [...host.relations, clone_component];
        } else {
          host.relations = [...host.relations, component];
          component.relations = [...component.relations, host];
        }
      }
    });
  }
  //#endregion

  //#region FormGrop and validation for Components
  formFill(components: CompTile[], hosts: HostTile[], form: FormGroup) {
    components.map((a) =>
      form.addControl(
        `${a.service_id}/${a.id}`,
        new FormControl(a.relations.length, this.validateConstraints(a, hosts.length))
      )
    );
  }

  /**
   * ```
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
  ```
 */
  validateConstraints(component: CompTile, hostLength: number) {
    const getError = (constraint: Constraint, relations: HostTile[]) => {
      if (!constraint?.length) return null;
      const [a1, a2, a3] = constraint;
      const countRelations = relations.length;
      const depend = () =>
        relations.some((a) => a.relations.some((b) => b.id === component.id))
          ? null
          : 'Must be installed because it is a dependency of another component';
      if (a3 && a3 === 'depend') return depend();
      else if (a2) {
        switch (a2) {
          case 'depend':
            return depend();
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
            return depend();
          case '+':
            return countRelations < hostLength ? 'Component should be installed on all hosts of cluster.' : null;
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

  setFormValue(c: CompTile, form: FormGroup) {
    form.controls[`${c.service_id}/${c.id}`].setValue(c.relations);
  }

  //#endregion

  //#region Removing links and dependencies

  clearDependencies(comp: CompTile, state: StatePost, cs: CompTile[], hs: HostTile[], form: FormGroup) {
    const getLimitsFromState = (prototype_id: number) => cs.find((b) => b.prototype_id === prototype_id).limit;
    if (comp.requires?.length) {
      this.findDependencies(comp, cs).forEach((a) => {
        a.limit = getLimitsFromState(a.prototype_id);
        a.notification = '';
      });

      state.data.map((a) =>
        this.checkDependencies(
          cs.find((b) => b.id === a.component_id),
          cs
        )
      );

      form.reset();
      this.formFill(cs, hs, form);
    }
  }

  findDependencies(c: CompTile, cs: CompTile[]) {
    const r =
      c.requires?.reduce((p, a) => [...p, ...a.components.map((b) => ({ prototype_id: b.prototype_id }))], []) || [];
    return cs.filter((a) => r.some((b) => b.prototype_id === a.prototype_id));
  }

  checkDependencies(c: CompTile, cs: CompTile[]) {
    this.findDependencies(c, cs).forEach((a) => (a.limit = a.limit ? [...a.limit, 'depend'] : ['depend']));
  }
  //#endregion

  //#region handler user events
  divorce(both: [CompTile, HostTile], cs: CompTile[], hs: HostTile[], state: StatePost, form: FormGroup) {
    both.forEach((a) => {
      a.relations = a.relations.filter((r) => r.id !== both.find((b) => b.id !== a.id).id);
      a.isLink = false;
    });

    const [component, host] = both;
    state.delete(new Post(host.id, component.service_id, component.id));
    this.clearDependencies(component, state, cs, hs, form);
    this.setFormValue(component, form);
  }

  next(
    target: Tile,
    stream: IStream,
    cs: CompTile[],
    hs: HostTile[],
    state: StatePost,
    load: StatePost,
    form: FormGroup
  ) {
    stream.linkSource.forEach((s) => (s.isLink = false));
    if (stream.selected) stream.selected.isSelected = false;

    if (stream.link) this.handleLink(stream.link, target, state, cs, hs, load, form);
    else if (stream.selected !== target) {
      target.isSelected = true;
      target.relations.forEach(
        (e) => (stream.linkSource.find((s) => s.name === e.name && s.id === e.id).isLink = true)
      );
    }
  }

  handleLink(
    link: Tile,
    target: Tile,
    state: StatePost,
    cs: CompTile[],
    hs: HostTile[],
    load: StatePost,
    form: FormGroup
  ) {
    const isComp = target instanceof CompTile;
    const component = (isComp ? target : link) as CompTile;
    const host = isComp ? link : target;
    const flag = (host_id: number, com: CompTile) =>
      load.data.some((a) => a.component_id === com.id && a.service_id === com.service_id && a.host_id === host_id);

    const checkActions = (host_id: number, com: CompTile, action: 'add' | 'remove'): boolean => {
      if (com.actions?.length) {
        if (action === 'remove') return flag(host_id, com) ? com.actions.some((a) => a === 'remove') : true;
        if (action === 'add') return flag(host_id, com) ? true : com.actions.some((a) => a === 'add');
      } else return true;
    };

    const noConstraint = (c: Constraint, r: number) => {
      if (!c?.length) return true;
      const v = c[c.length - 1];
      return v === '+' || v === 'odd' || v > r || v === 'depend';
    };

    if (link.relations.find((e) => e.id === target.id)) {
      if (checkActions(host.id, component, 'remove')) this.divorce([component, host], cs, hs, state, form);
      return;
    } else if (noConstraint(component.limit, component.relations.length)) {
      if (!checkActions(host.id, component, 'add')) return;
      if (component.requires?.length) {
        const requires = component.requires.reduce(
          (p, c) => (c.components.some((a) => cs.some((b) => b.prototype_id === a.prototype_id)) ? p : [...p, c]),
          []
        );
        if (requires.length) {
          this.dialog4Requires(requires);
          return;
        } else {
          this.checkDependencies(component, cs);
          form.reset();
          this.formFill(cs, hs, form);
        }
      }
      link.relations.push(target);
      target.relations.push(link);
      target.isLink = true;
      state.add(new Post(host.id, component.service_id, component.id));
    }
    this.setFormValue(component, form);
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
  //#endregion
}
