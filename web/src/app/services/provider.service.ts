import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { EntityService } from '../abstract/entity-service';
import { Provider } from '../core/types';
import { environment } from '../../environments/environment';
import { ApiService } from '../core/api';

@Injectable({
  providedIn: 'root',
})
export class ProviderService extends EntityService<Provider> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<Provider> {
    return this.api.get(`${environment.apiRoot}provider/${id}/`, params);
  }

}
