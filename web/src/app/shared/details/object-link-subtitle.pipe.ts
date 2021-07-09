import { Pipe, PipeTransform } from '@angular/core';
import { JobObject } from '@app/core/types';
import { ObjectsHelper } from '@app/helpers/objects-helper';

@Pipe({
  name: 'objectLinkSubtitle'
})
export class ObjectLinkSubtitlePipe implements PipeTransform {

  transform(object: JobObject, objects: JobObject[]): string[] {
    return ObjectsHelper.getObjectUrl(object, ObjectsHelper.sortObjects(objects));
  }

}
