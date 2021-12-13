import { Observable } from 'rxjs';
import { Params } from '@angular/router';
import { FormModel } from '@app/shared/add-component/add-service-model';

export abstract class EntityAbstractService {
  abstract model(value?: any): FormModel;

  abstract delete(id: number): Observable<any>;

  abstract add(param: any): Observable<any>;

  abstract update(url: string, params?: Partial<any>): Observable<any>;

  abstract getList(param?: Params): Observable<any[]>;
}
