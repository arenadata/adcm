import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { EntityService } from '../abstract/entity-service';
import { Bundle } from '../core/types';
import { ApiService } from '../core/api';
import { environment } from '@env/environment';

@Injectable({
  providedIn: 'root',
})
export class BundleService extends EntityService<Bundle> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<Bundle> {
    return this.api.get(`${environment.apiRoot}stack/bundle/${id}/`, params);
  }

}
