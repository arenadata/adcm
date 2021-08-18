import { Injectable } from '@angular/core';
import { FormModel, IAddService } from '../../shared/add-component/add-service-token';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { ClusterService } from '../../core/services/cluster.service';
import { Host, TypeName } from '../../core/types';
import { Params } from '@angular/router';
import { Observable } from 'rxjs';
import { of } from 'rxjs/internal/observable/of';
import { ApiService } from '../../core/api';
import { environment } from '../../../environments/environment';
import { ConfigGroup } from '../model/config-group.model';

const newConfigGroupForm = () =>
  new FormGroup({
    name: new FormControl('', Validators.required),
    description: new FormControl(),
  });

@Injectable({
  providedIn: 'root'
})
export class ConfigGroupAddService implements IAddService {

  get Cluster() {
    return this.service.Cluster;
  }

  get Current() {
    return this.service.Current;
  }

  constructor(private service: ClusterService, protected api: ApiService) {}

  model(name?: string): FormModel {
    return {
      name: 'group_configs',
      title: 'Config group',
      form: newConfigGroupForm()
    };
  }

  add(group: Partial<ConfigGroup>): Observable<any> {
    const params = { ...group };
    params.object_type = 'cluster';
    params.object_id = this.Cluster.id;
    return this.api.post<unknown>(`${environment.apiRoot}group-config/`, params);
  }

  getList<T>(type: TypeName, param: Params = {}): Observable<T[]> {
    return of([]);
  }

  addHost(host: Partial<Host>): Observable<Host> {
    return of(null);
  }

}
