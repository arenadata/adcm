import { Observable } from 'rxjs';
import { Params } from '@angular/router';
import { FormModel } from '@app/shared/add-component/add-service-model';

export abstract class EntityAbstractService<T = any> {
  abstract model?(value?: any): FormModel;

  abstract delete?(id: number): Observable<T>;

  abstract add?(param: any): Observable<T>;

  abstract get?(id: number): Observable<T>;

  abstract getByUrl?(url: string): Observable<T>;

  abstract update?(url: string, params?: Partial<any>): Observable<T>;

  abstract getList?(param?: Params): Observable<any[]>;
}
