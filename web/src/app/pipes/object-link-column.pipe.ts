import { Pipe, PipeTransform } from '@angular/core';
import { ILinkColumn } from '@adwp-ui/widgets';

import { JobObject, Task } from '../core/types';
import { ObjectsHelper } from '../helpers/objects-helper';

@Pipe({
  name: 'objectLinkColumn'
})
export class ObjectLinkColumnPipe implements PipeTransform {

  getCluster(task: Task) {
    return ObjectsHelper.getObject(task.objects, 'cluster');
  }

  getService(task: Task) {
    return ObjectsHelper.getObject(task.objects, 'service');
  }

  url(object: JobObject, task: Task): string[] {
    if (object.type === 'cluster' || !this.getCluster(task)) {
      return ['/', object.type, `${object.id}`];
    } else if (object.type === 'component' && this.getService(task)) {
      return ['/', 'cluster', `${this.getCluster(task).id}`, 'service', `${this.getService(task).id}`, object.type, `${object.id}`];
    } else {
      return ['/', 'cluster', `${this.getCluster(task).id}`, object.type, `${object.id}`];
    }
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
