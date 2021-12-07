import { Pipe, PipeTransform } from '@angular/core';
import { Observable } from 'rxjs';

@Pipe({
  name: 'groups'
})
export class GroupsToOptionsPipe implements PipeTransform {
  transform(relations: Map<string, Observable<any>>): Observable<any[]> {
    return relations.get('groups');
  }

}
