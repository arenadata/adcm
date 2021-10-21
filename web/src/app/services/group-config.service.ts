import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { EntityService } from '../abstract/entity-service';
import { ApiService } from '../core/api';
import { environment } from '@env/environment';
import { ConfigGroup } from '../config-groups';

@Injectable({
  providedIn: 'root',
})
export class GroupConfigService extends EntityService<ConfigGroup> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<ConfigGroup> {
    return this.api.get(`${environment.apiRoot}stack/bundle/${id}/`, params);
  }

}
