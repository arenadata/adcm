import { Injectable } from '@angular/core';
import { FormModel, IAddService } from '../../shared/add-component/add-service-model';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { ClusterService } from '../../core/services/cluster.service';
import { Observable } from 'rxjs';
import { ApiService } from '../../core/api';
import { ConfigGroup } from '../model';
import { environment } from '../../../environments/environment';

const newConfigGroupForm = (): FormGroup =>
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

  add<T>(group: Partial<ConfigGroup>): Observable<T> {
    const params = { ...group };
    params.object_type = this.service.Current.typeName;
    params.object_id = this.service.Current.id;
    return this.api.post<T>(`${environment.apiRoot}group-config/`, params);
  }

}
