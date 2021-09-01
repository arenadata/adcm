import { Injectable } from '@angular/core';
import { FormModel, IAddService } from '@app/shared/add-component/add-service-model';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { ClusterService } from '@app/core/services/cluster.service';
import { Host, TypeName } from '../../core/types';
import { convertToParamMap, Params } from '@angular/router';
import { forkJoin, Observable } from 'rxjs';
import { ApiService } from '@app/core/api';
import { environment } from '@env/environment';
import { map } from 'rxjs/operators';
import { ConfigGroup } from '@app/config-groups';

const newConfigGroupHostForm = () =>
  new FormGroup({
    name: new FormControl('', Validators.required),
    description: new FormControl(),
  });

@Injectable({
  providedIn: 'root'
})
export class ConfigGroupHostAddService implements IAddService {

  get Cluster() {
    return this.service.Cluster;
  }

  get Current() {
    return this.service.Current;
  }

  constructor(private service: ClusterService, protected api: ApiService) {}

  model(name?: string): FormModel {
    return {
      name: 'host2configgroup',
      title: 'Config group hosts',
      form: newConfigGroupHostForm()
    };
  }

  add(data: { host: number, group: number }[]): Observable<any> {
    return forkJoin(data.map((o) => this.api.post<unknown>(`${environment.apiRoot}group-config-host/`, o)));
  }

  getList(type: TypeName, param: Params = {}): Observable<any[]> {
    const paramMap = convertToParamMap(param);
    const current = this.Current as unknown as ConfigGroup;

    return this.api.getList<Host>(current.host_candidate, paramMap).pipe(
      map(({ results }) => results.map((host) => ({ ...host, name: host.fqdn })))
    );
  }

}
