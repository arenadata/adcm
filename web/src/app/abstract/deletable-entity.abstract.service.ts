import { Observable } from 'rxjs';

export abstract class DeletableEntityAbstractService {

  abstract delete(id: number): Observable<any>;

}
