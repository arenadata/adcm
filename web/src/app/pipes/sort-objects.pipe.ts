import { Pipe, PipeTransform } from '@angular/core';

import { JobObject } from '../core/types';
import { ObjectsHelper } from '../helpers/objects-helper';

@Pipe({
  name: 'sortObjects'
})
export class SortObjectsPipe implements PipeTransform {

  transform(objects: JobObject[]): JobObject[] {
    if (ObjectsHelper.getObject(objects, 'component')) {
      return [
        ObjectsHelper.getObject(objects, 'component'),
        ObjectsHelper.getObject(objects, 'service'),
        ObjectsHelper.getObject(objects, 'cluster'),
      ];
    }

    return objects;
  }

}
