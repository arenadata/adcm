import { InjectionToken } from '@angular/core';
import { TypeName } from '@app/core/types';
import { ParamMap } from '@angular/router';
import { Observable } from 'rxjs';
import { ListResult } from '@app/models/list-result';

export const LIST_SERVICE_PROVIDER = new InjectionToken<IListService<any>>('ListService');

export interface ListInstance {
  typeName: TypeName;
  columns: string[];
}

export interface IListService<T> {
  current: ListInstance;

  initInstance(typeName?: TypeName): ListInstance;

  getList(p: ParamMap, typeName?: string): Observable<ListResult<T>>

  delete(row: T): Observable<Object>;
}
