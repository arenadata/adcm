import { Pipe, PipeTransform } from '@angular/core';
import { ILinkColumn } from '@adwp-ui/widgets';

import { JobObject, Task } from '../../../core/types';
import { ObjectsHelper } from '@app/helpers/objects-helper';

@Pipe({
  name: 'objectLinkColumn'
})
export class ObjectLinkColumnPipe implements PipeTransform {

  getCluster(jobs: JobObject[]) {
    return ObjectsHelper.getObject(jobs, 'cluster');
  }

  getService(jobs: JobObject[]) {
    return ObjectsHelper.getObject(jobs, 'service');
  }

  url(object: JobObject, jobs: JobObject[]): string[] {
    if (object.type === 'cluster' || !this.getCluster(jobs)) {
      return ['/', object.type, `${object.id}`];
    } else if (object.type === 'component' && this.getService(jobs)) {
      return ['/', 'cluster', `${this.getCluster(jobs).id}`, 'service', `${this.getService(jobs).id}`, object.type, `${object.id}`];
    } else {
      return ['/', 'cluster', `${this.getCluster(jobs).id}`, object.type, `${object.id}`];
    }
  }

  transform(object: JobObject, jobs: JobObject[]): ILinkColumn<Task> {
    return {
      label: '',
      type: 'link',
      value: () => object.name,
      url: () => this.url(object, jobs).join('/'),
    };
  }

}
