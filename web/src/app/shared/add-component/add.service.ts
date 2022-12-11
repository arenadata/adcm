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
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { convertToParamMap, Params } from '@angular/router';
import { environment } from '@env/environment';
import { forkJoin, Observable, of, throwError } from 'rxjs';
import { catchError, concatAll, filter, map, switchMap } from 'rxjs/operators';

import { StackInfo, StackService } from '@app/core/services';
import { ClusterService } from '@app/core/services/cluster.service';
import { ApiService } from '@app/core/api';
import { Host, Prototype, ServicePrototype, StackBase, TypeName } from '@app/core/types';
import { DialogComponent } from '@app/shared/components/dialog.component';
import { GenName } from './naming';
import { MainService } from '@app/shared/configuration/main/main.service';
import { FormModel, IAddService } from '@app/shared/add-component/add-service-model';


const fromBundle = () =>
  new FormGroup({
    prototype_id: new FormControl('', Validators.required),
    name: new FormControl('', Validators.required),
    description: new FormControl(),
  });

const MODELS: { [key: string]: FormModel } = {
  provider: {
    name: 'provider',
    form: fromBundle(),
  },
  host: {
    name: 'host',
    form: new FormGroup({
      fqdn: new FormControl('', [
        Validators.required,
        Validators.maxLength(253),
        Validators.pattern(new RegExp(/^[A-Za-z0-9]{1}[A-Za-z0-9.-]*$/))
      ]),
      cluster_id: new FormControl(),
      provider_id: new FormControl('', Validators.required),
    }),
  },
  cluster: {
    name: 'cluster',
    form: fromBundle(),
  },
  service: {
    name: 'service',
    title: 'services'
  },
  host2cluster: {
    name: 'host2cluster',
    title: 'hosts',
  },
};

@Injectable({
  providedIn: 'root',
})
export class AddService implements IAddService {
  private _currentPrototype: StackBase;
  set currentPrototype(a: StackBase) {
    this._currentPrototype = a;
  }

  get currentPrototype(): StackBase {
    return this._currentPrototype;
  }

  constructor(private api: ApiService,
              private stack: StackService,
              private cluster: ClusterService,
              public dialog: MatDialog,
              private main: MainService,
  ) {}

  model(name: string) {
    return MODELS[name];
  }

  get Cluster() {
    return this.cluster.Cluster;
  }

  get Current() {
    return this.main.Current;
  }

  genName(form: FormGroup) {
    return form
      .get('prototype_id')
      .valueChanges.pipe(filter((v) => !!v))
      .subscribe(() => {
        const field = form.get('name');
        if (!field.value) field.setValue(GenName.do());
      });
  }

  add<T>(data: Partial<T>, name: TypeName, prototype?: StackBase) {
    const currentPrototype = prototype || this.currentPrototype;
    if (currentPrototype?.license === 'unaccepted') {
      return this.api.root.pipe(
        switchMap((root) =>
          this.api.get<{ text: string }>(`${root.stack}bundle/${currentPrototype.bundle_id}/license/`).pipe(
            switchMap((info) =>
              this.dialog
                .open(DialogComponent, {
                  data: {
                    title: `Accept license agreement`,
                    text: info.text,
                    controls: { label: 'Do you accept the license agreement?', buttons: ['Yes', 'No'] },
                  },
                })
                .beforeClosed()
                .pipe(
                  filter((yes) => yes),
                  switchMap(() =>
                    this.api.put(`${root.stack}bundle/${currentPrototype.bundle_id}/license/accept/`, {}).pipe(switchMap(() => this.api.post<T>(root[name], data)))
                  )
                )
            )
          )
        )
      );
    } else return this.api.root.pipe(switchMap((root) => this.api.post<T>(root[name], data)));
  }

  addHost(host: Partial<Host>): Observable<Host> {
    const a$ = this.api.post<Host>(`${environment.apiRoot}provider/${host.provider_id}/host/`, { fqdn: host.fqdn });
    const b$ = a$.pipe(
      map((h) => (host.cluster_id ? this.api.post<Host>(`${environment.apiRoot}cluster/${host.cluster_id}/host/`, { host_id: h.id }) : of(h)))
    );
    return b$.pipe(concatAll());
  }

  addHostInCluster(ids: number[]) {
    return forkJoin([...ids.map(id => this.cluster.addHost(id))]);
  }

  addService(data: { prototype_id: number, name?: string, licence_url?: string }[]) {
    return this.cluster.addServices(data);
  }

  getListResults<T>(type: TypeName, param: Params = {}) {
    const paramMap = convertToParamMap(param);
    return this.api.root.pipe(switchMap((root) => this.api.getList<T>(root[type], paramMap)));
  }

  getList<T>(type: TypeName, param: Params = {}): Observable<T[]> {
    return this.getListResults<T>(type, param).pipe(map((list) => list.results));
  }

  getPrototype(name: StackInfo, param: { [key: string]: string | number }): Observable<Prototype[]> {
    return this.stack.fromStack(name, param);
  }

  getProtoServiceForCurrentCluster() {
    return this.api.get<StackBase[]>(this.cluster.Cluster?.serviceprototype).pipe(
      map((a: ServicePrototype[]) =>
        a
          .filter((b) => !b.selected)
          .map((b) => ({
            ...b,
            name: `${b.display_name} - ${b.version}`,
          }))
      )
    );
  }

  upload(data: FormData[]) {
    return this.stack.upload(data).pipe(catchError((e) => throwError(e)));
  }

  getHostListForCurrentCluster() {
    return this.api.get<Host[]>(this.cluster.Cluster?.host).pipe(
      map((hosts) =>
        hosts
          .map((host) => ({
            ...host,
            name: host.fqdn,
          }))
      )
    );
  }

}
