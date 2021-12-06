import { Observable } from 'rxjs';
import { Params } from '@angular/router';

export abstract class EntityAbstractService {

  abstract delete(id: number): Observable<any>;

  abstract add<T>(param: Partial<T>): Observable<T>;

  abstract update<T>(url: string, params?: Partial<T>): Observable<T>

  abstract getList<T>(param?: Params): Observable<T[]>;
}
