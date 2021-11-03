import { Observable } from 'rxjs';

import { StatusTree, StatusTreeSubject } from '../models/status-tree';

export abstract class HavingStatusTreeAbstractService<StatusTreeType extends StatusTreeSubject> {

  abstract getStatusTree(id: number): Observable<StatusTreeType>;
  abstract entityStatusTreeToStatusTree(input: StatusTreeType): StatusTree[];

}
