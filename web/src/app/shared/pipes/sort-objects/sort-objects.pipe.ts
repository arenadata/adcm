import { Pipe, PipeTransform } from '@angular/core';

import { JobObject } from '@app/core/types';
import { ObjectsHelper } from '@app/helpers/objects-helper';

@Pipe({
  name: 'sortObjects'
})
export class SortObjectsPipe implements PipeTransform {

  transform(objects: JobObject[]): JobObject[] {
    return [
      ObjectsHelper.getObject(objects, 'host'),
      ObjectsHelper.getObject(objects, 'provider'),
      ObjectsHelper.getObject(objects, 'component'),
      ObjectsHelper.getObject(objects, 'service'),
      ObjectsHelper.getObject(objects, 'cluster'),
    ].filter((object) => !!object);
  }

}
