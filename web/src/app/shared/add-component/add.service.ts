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
import { EventEmitter, Injectable } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { ClusterService, StackInfo, StackService } from '@app/core';
import { ApiService } from '@app/core/api';
import { Prototype, Provider, ServicePrototype, StackBase, TypeName } from '@app/core/types';
import { Cluster, Host } from '@app/core/types/api';
import { environment } from '@env/environment';
import { Observable, of } from 'rxjs';
import { concatAll, filter, map, switchMap } from 'rxjs/operators';

import { DialogComponent } from '../components/dialog.component';
import { ListResult } from '../components/list/list.component';

export interface FormModel {
  name: string;
  title?: string;
  form?: FormGroup;
  success?: EventEmitter<{ flag: boolean; obj: any }>;
}

const fromBundle = new FormGroup({
  prototype_id: new FormControl('', Validators.required),
  name: new FormControl('', Validators.required),
  description: new FormControl()
});

const MODELS: { [key: string]: FormModel } = {
  provider: {
    title: 'hostprovider',
    name: 'provider',
    form: fromBundle
  },
  host: {
    name: 'host',
    form: new FormGroup({
      fqdn: new FormControl('', [Validators.required, Validators.pattern(new RegExp(/^[A-Za-z0-9_\.\-]+$/))]),
      cluster_id: new FormControl(),
      provider_id: new FormControl('', Validators.required)
    })
  },
  cluster: {
    name: 'cluster',
    form: fromBundle
  },
  service: {
    name: 'service',
    title: 'service'
  },
  host2cluster: {
    name: 'host2cluster',
    title: 'free host'
  }
};

@Injectable({
  providedIn: 'root'
})
export class AddService {
  currentPrototype: StackBase;
  constructor(private api: ApiService, private stack: StackService, private cluster: ClusterService, public dialog: MatDialog) {}

  model(name: string) {
    return MODELS[name];
  }

  get Cluster() {
    return this.cluster.Cluster;
  }

  add<T>(data: Partial<T>, name: TypeName) {
    if (this.currentPrototype && this.currentPrototype.license === 'unaccepted') {
      return this.api.root.pipe(
        switchMap(root =>
          this.api.get<{ text: string }>(`${root.stack}bundle/${this.currentPrototype.bundle_id}/license/`).pipe(
            switchMap(info =>
              this.dialog
                .open(DialogComponent, {
                  data: {
                    title: `Accept license agreement`,
                    text: info.text,
                    controls: { label: 'Do you accept the license agreement?', buttons: ['Yes', 'No'] }
                  }
                })
                .beforeClosed()
                .pipe(
                  filter(yes => yes),
                  switchMap(() =>
                    this.api
                      .put(`${root.stack}bundle/${this.currentPrototype.bundle_id}/license/accept/`, {})
                      .pipe(switchMap(() => this.api.post<T>(root[name], data)))
                  )
                )
            )
          )
        )
      );
    } else return this.api.root.pipe(switchMap(root => this.api.post<T>(root[name], data)));
  }

  addHost(host: Partial<Host>): Observable<Host> {
    const a$ = this.api.post<Host>(`${environment.apiRoot}provider/${host.provider_id}/host/`, { fqdn: host.fqdn });
    const b$ = a$.pipe(
      map(h => (host.cluster_id ? this.api.post<Host>(`${environment.apiRoot}cluster/${host.cluster_id}/host/`, { host_id: h.id }) : of(h)))
    );
    return b$.pipe(concatAll());
  }

  addHostInCluster(host: Host) {
    return this.cluster.addHost(host);
  }

  addService(data: { prototype_id: number }[]) {
    return this.cluster.addServices(data);
  }

  getClusters(param: { [key: string]: string | number } = {}) {
    const limit = param.limit ? +param.limit : +localStorage.getItem('limit'),
      offset = (param.page ? +param.page : 0) * limit;
    return this.api.root.pipe(
      switchMap(root =>
        this.api
          .get<ListResult<Cluster>>(root.cluster, {
            limit: limit.toString(),
            offset: offset.toString(),
            ordering: 'display_name'
          })
          .pipe(map(list => list.results))
      )
    );
  }

  getProviders() {
    return this.api.getPure<Provider>('provider', { ordering: 'name' });
  }

  getPrototype(name: StackInfo, param: { [key: string]: string | number }): Observable<Prototype[]> {
    return this.stack.fromStack(name, param);
  }

  getProtoServiceForCurrentCluster() {
    return this.api.get<StackBase[]>(this.cluster.Cluster.serviceprototype).pipe(
      map((a: ServicePrototype[]) =>
        a
          .filter(b => !b.selected)
          .map(b => ({
            ...b,
            name: `${b.display_name} - ${b.version}`
          }))
      )
    );
  }

  getFreeHosts() {
    return this.api
      .getPure<Host>('host', { cluster_is_null: 'true' })
      .pipe(map(a => a.map(b => ({ ...b, name: b.fqdn }))));
  }

  upload(data: FormData[]) {
    return this.stack.upload(data);
  }

  setBundle(id: number, proto: StackBase[]) {
    if (id && proto.length) {
      this.currentPrototype = proto.find(a => a.id === id);
    }
  }
}
