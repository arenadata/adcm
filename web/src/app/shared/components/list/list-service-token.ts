import { InjectionToken } from '@angular/core';
import { TypeName } from '@app/core/types';

export const LIST_SERVICE_PROVIDER = new InjectionToken<IListService>('ListService');

export interface ListInstance {
  typeName: TypeName;
  columns: string[];
}

export interface IListService {
  current: ListInstance;

  initInstance(typeName?: TypeName): ListInstance;
}
