import { Pipe, PipeTransform } from '@angular/core';

import { TaskRaw } from '@app/core/types';

@Pipe({
  name: 'bellTaskLink'
})
export class BellTaskLinkPipe implements PipeTransform {

  transform(task: TaskRaw): (string | number)[] {
    if (task.status === 'failed' && task?.jobs?.length > 1) {
      const failedJob = task.jobs.find(job => job.status === 'failed');
      if (failedJob) {
        return ['job', failedJob.id, 'main'];
      }
    }

    return ['job', task.id, 'main'];
  }

}
