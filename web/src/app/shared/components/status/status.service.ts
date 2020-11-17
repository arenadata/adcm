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
import { Cluster, IComponent, Host, HostComponent, Service } from '@app/core/types';
import { combineLatest, Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export interface StatusInfo {
  id: number;
  name: string;
  status: number;
  relations: {
    id: number;
    name: string;
    status: number;
    components: { id: number; name: string; status: number }[];
  }[];
}

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

  getServiceComponentsByCluster(cluster: Cluster, service_id?: number): Observable<IComponent[]> {
    return this.api.get<IComponent[]>(cluster.status_url).pipe(map((s) => s.filter((se) => (service_id ? se.service_id === service_id : true))));
  }

  getHostcomponentStatus(k: HostComponent, all: IAllStatus) {
    const c = all.services[k.service_id]?.details.find((e) => +e.host === k.host_id && +e.component === k.component_id);
    return c ? c.status : null;
  }

  /**
   *
   */
  fillStatus(a: [IAllStatus, HostComponent[]], host_id?: number, service_id?: number): StatusInfo[] {
    const all: IAllStatus = a[0],
      hc: HostComponent[] = a[1];

    const findComponents = (e: HostComponent) =>
      hc
        .filter((k) => k.host_id === e.host_id && k.service_id === e.service_id)
        .filter((k) => k.monitoring !== 'passive')
        .map((k) => ({
          id: k.component_id,
          name: k.component_display_name,
          status: this.getHostcomponentStatus(k, all),
        }));

    const findServices = (id: number) =>
      hc
        .filter((b) => (service_id ? b.host_id === id && b.service_id === service_id : b.host_id === id))
        .reduce((acc, cur) => (!acc.some((c) => c.service_id === cur.service_id) ? [...acc, cur] : acc), [])
        .map((e) => ({
          id: e.service_id,
          name: e.service_display_name || e.service_name,
          status: (all as IAllStatus).services[e.service_id]?.status,
          components: findComponents(e),
        }))
        .filter((z) => z.components.length);

    return hc
      .filter((h) => (host_id ? h.host_id === host_id : true))
      .reduce((acc, cur) => (!acc.some((c) => c.host_id === cur.host_id) ? [...acc, cur] : acc), [])
      .map((b) => ({
        name: b.host,
        id: b.host_id,
        status: (all as IAllStatus).hosts[b.host_id] ? (all as IAllStatus).hosts[b.host_id]?.status : null,
        relations: findServices(b.host_id),
      }))
      .filter((z) => z.relations.length);
  }

  fillStatusByService(a: [IAllStatus, HostComponent[]], service_id?: number): StatusInfo[] {
    const all: IAllStatus = a[0],
      hc: HostComponent[] = a[1];

    const findHost = (hoc: HostComponent) =>
      hc
        .filter((b) => b.component_id === hoc.component_id)
        .reduce((acc, cur) => (!acc.some((c) => c.host_id === cur.host_id) ? [...acc, cur] : acc), [])
        .map((e) => ({
          id: e.host_id,
          name: e.host,
          status: (all as IAllStatus).hosts[e.host_id]?.status,
        }));

    const findComponents = (id: number) =>
      hc
        .filter((b) => (service_id ? b.service_id === id && b.service_id === service_id : b.service_id === id))
        .filter((b) => b.monitoring !== 'passive')
        .reduce((acc, cur) => (!acc.some((c) => c.component_id === cur.component_id) ? [...acc, cur] : acc), [])
        .map((e) => ({
          id: e.component_id,
          name: e.component_display_name || e.component,
          status: this.getHostcomponentStatus(e, all),
          components: findHost(e),
        }))
        .filter((z) => z.components.length);

    return hc
      .filter((s) => (service_id ? s.service_id === service_id : true))
      .reduce((acc, cur) => (!acc.some((c) => c.service_id === cur.service_id) ? [...acc, cur] : acc), [])
      .map((b) => ({
        name: b.service_display_name || b.service,
        id: b.service_id,
        status: (all as IAllStatus).services[b.service_id]?.status,
        relations: findComponents(b.service_id),
      }))
      .filter((z) => z.relations.length);
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
    return this.api.getOne<Cluster>('cluster', id);
  }

  getAllClusterStatus(id: number) {
    return this.api.get<IAllStatus>(`/status/api/v1/cluster/${id}/`);
  }

  getHostStatus(host: Host, cid: number) {
    return this.api.get<IStatus>(`/status/api/v1/cluster/${cid}/host/${host.id}/`).pipe(map((c) => ({ ...host, ...c })));
  }

  getServiceStatus(s: Service, cluster_id: number) {
    return this.api.get<IStatus>(`/status/api/v1/cluster/${cluster_id}/service/${s.id}/`).pipe(map((c) => ({ ...s, ...c })));
  }

  getHostComponentStatus(hc: HostComponent) {
    return this.api.get<IStatus>(`/status/api/v1/host/${hc.host_id}/component/${hc.component_id}/`).pipe(map((c) => ({ ...hc, ...c })));
  }

  updateHostStatus(id: string, cid: number, value: number) {
    return this.api.post(`/status/api/v1/cluster/${cid}/host/${id}/`, { status: value });
  }

  updateHcStatus(hid: string, cid: string, value: number) {
    return this.api.post(`/status/api/v1/host/${hid}/component/${cid}/`, { status: value });
  }
}
