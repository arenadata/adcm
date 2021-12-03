import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '@app/core/api';
import { environment } from '@env/environment';
import { DeletableEntityAbstractService } from '@app/abstract/deletable-entity.abstract.service';

@Injectable()
export class RbacGroupService implements DeletableEntityAbstractService {

  constructor(
    protected api: ApiService,
  ) {}

  delete(id: number): Observable<unknown> {
    return this.api.delete(`${environment.apiRoot}rbac/group/${id}/`);
  }

}
