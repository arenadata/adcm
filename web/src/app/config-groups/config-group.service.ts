import { Injectable } from '@angular/core';
import { forkJoin, Observable } from 'rxjs';
import { EntityService } from '@app/abstract/entity-service';
import { ApiService } from '@app/core/api';
import { ConfigGroup } from '@app/config-groups/config-group.model';
import { IConfigGroup, TypeName } from '@app/core/types';
import { map } from 'rxjs/operators';
import { environment } from '@env/environment';

@Injectable({
  providedIn: 'root'
})
export class ConfigGroupService extends EntityService<ConfigGroup> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(id: number, params: { [key: string]: string } = {}): Observable<ConfigGroup> {
    return this.api.get<IConfigGroup>(`api/v1/config-group/${id}`, params).pipe(
      map((response) => new ConfigGroup(response))
    );
  }

  add(object_type: TypeName, object_id: number, data: Partial<ConfigGroup>) {
    const params = { object_type, object_id, ...data };

    return this.api.post<any>(`${environment.apiRoot}config-group/`, params);
  }

  addHosts(data: { host: number, group: number }[]) {
    return forkJoin(data.map((o) => this.api.post<unknown>(`${environment.apiRoot}host-group/`, o)));
  }
}
