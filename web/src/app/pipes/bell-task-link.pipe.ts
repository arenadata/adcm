import { Pipe, PipeTransform } from '@angular/core';

import { TaskRaw } from '@app/core/types';

@Pipe({
  name: 'bellTaskLink'
})
export class BellTaskLinkPipe implements PipeTransform {

  transform(task: TaskRaw): (string | number)[] {
    if (task?.jobs?.length > 0) {
      if (task.status === 'failed') {
        const failedJob = task.jobs.find(job => job.status === 'failed');
        if (failedJob) {
          return ['job', failedJob.id, 'main'];
        }
      } else {
        return ['job', task.jobs[0].id, 'main'];
      }
    }

    return ['job', task.id, 'main'];
  }

}
