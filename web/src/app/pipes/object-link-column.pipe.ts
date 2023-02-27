import { Pipe, PipeTransform } from '@angular/core';
import { ILinkColumn } from '@app/adwp';

import { JobObject, Task } from '../core/types';
import { ObjectsHelper } from '../helpers/objects-helper';

@Pipe({
  name: 'objectLinkColumn'
})
export class ObjectLinkColumnPipe implements PipeTransform {

  url(object: JobObject, task: Task): string[] {
    return ObjectsHelper.getObjectUrl(object, task.objects);
  }

  transform(object: JobObject, task: Task): ILinkColumn<Task> {
    return {
      label: '',
      type: 'link',
      value: () => object.name,
      url: () => this.url(object, task).join('/'),
    };
  }

}
