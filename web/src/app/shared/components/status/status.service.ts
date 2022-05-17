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
import { combineLatest, Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { ApiService } from '@app/core/api';
import { IComponent, Host, HostComponent } from '@app/core/types';
import { ICluster } from '@app/models/cluster';

interface IStatus {
  [key: number]: { status: number };
}

export interface IAllStatus {
  hosts: IStatus;
  services: { details: [{ host: string | number; component: string | number; status: number }]; status: number }[];
  components: IStatus;
  status: number;
}

@Injectable({
  providedIn: 'root',
})
export class StatusService {
  constructor(private api: ApiService) { }

  getStatusInfo(id: number, hostcomponent_link: string) {
    const statuses$ = this.getAllClusterStatus(id),
      host_components$ = this.getHostComponents(hostcomponent_link);
    return combineLatest([statuses$, host_components$]);
  }

  getHostComponents(url: string): Observable<HostComponent[]> {
    return this.api
      .get<{ host: Host[]; hc: HostComponent[]; component: IComponent[] }>(url)
      .pipe(map((a) => a.hc.map((hc) => ({ ...hc, monitoring: a.component.find((b) => b.id === hc.component_id).monitoring }))));
  }

  getServiceComponentsByCluster(cluster: ICluster, service_id?: number): Observable<IComponent[]> {
    return this.api.get<IComponent[]>(cluster.status_url).pipe(map((s) => s.filter((se) => (service_id ? se.service_id === service_id : true))));
  }

  getHostcomponentStatus(k: HostComponent, all: IAllStatus) {
    const c = all.services[k.service_id]?.details.find((e) => +e.host === k.host_id && +e.component === k.component_id);
    return c ? c.status : null;
  }

  getComponentsOnly(a: [IAllStatus, HostComponent[]], host_id?: number) {
    const all: IAllStatus = a[0],
      hc: HostComponent[] = a[1];
    return hc
      .filter((h) => (host_id ? host_id === h.host_id : true))
      .reduce((acc, cur) => (!acc.some((c) => c.host_id === cur.host_id && c.service_id === cur.service_id) ? [...acc, cur] : acc), [])
      .map((k) => ({ ...k, status: this.getHostcomponentStatus(k, all) }))
      .filter((b) => b.status !== 0);
  }

  getClusterById(id: number) {
    return this.api.getOne<ICluster>('cluster', id);
  }

  getAllClusterStatus(id: number) {
    return this.api.get<IAllStatus>(`/status/api/v1/cluster/${id}/`);
  }

}
