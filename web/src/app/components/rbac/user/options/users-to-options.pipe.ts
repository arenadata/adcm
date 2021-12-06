import { Pipe, PipeTransform } from '@angular/core';
import { Observable } from 'rxjs';

@Pipe({
  name: 'users'
})
export class UsersToOptionsPipe implements PipeTransform {

  transform(relations: Map<string, Observable<any>>): Observable<any[]> {
    return relations.get('users');
  }

}
