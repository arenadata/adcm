import { Pipe, PipeTransform } from '@angular/core';
import { ILinkColumn } from '@adwp-ui/widgets';
import { JobObject, Task } from '../core/types';

@Pipe({
  name: 'objectLinkColumn'
})
export class ObjectLinkColumnPipe implements PipeTransform {

  transform(object: JobObject, task: Task): ILinkColumn<Task> {
    const c = task.objects.find((a) => a.type === 'cluster');
    const url = (a: JobObject): string[] => (a.type === 'cluster' || !c ? ['/', a.type, `${a.id}`] : ['/', 'cluster', `${c.id}`, a.type, `${a.id}`]);

    return {
      label: '',
      type: 'link',
      value: () => object.name,
      url: () => url(object).join('/'),
    };
  }

}
