import { Observable } from 'rxjs';

export interface RelationList<T> {
  [key: string]: Observable<T>;
}
