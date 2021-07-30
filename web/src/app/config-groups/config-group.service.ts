import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { EntityService } from '@app/abstract/entity-service';
import { ApiService } from '@app/core/api';
import { ConfigGroup } from '@app/config-groups/config-group.model';
import { IConfigGroup } from '@app/core/types';
import { map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class ConfigGroupService extends EntityService<any> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<ConfigGroup> {
    return this.api.get<IConfigGroup>(`api/v1/config-group/${id}`, params).pipe(
      map((response) => new ConfigGroup(response))
    );
  }
}
