import { Pipe, PipeTransform } from '@angular/core';

import { TaskRaw } from '@app/core/types';

@Pipe({
  name: 'bellTaskLink'
})
export class BellTaskLinkPipe implements PipeTransform {

  endStatuses = ['aborted', 'success', 'failed'];

  transform(task: TaskRaw): (string | number)[] {
    if (task?.jobs?.length > 0) {
      if (task.status === 'running') {
        const runningJob = task.jobs.find(job => job.status === 'running');
        if (runningJob) {
          return ['job', runningJob.id, 'main'];
        }

        const createdJob = task.jobs.find(job => job.status === 'created');
        if (createdJob) {
          return ['job', createdJob.id, 'main'];
        }

        const descOrderedJobs = task.jobs.slice().reverse();
        const finishedJob = descOrderedJobs.find(job => this.endStatuses.includes(job.status));
        if (finishedJob) {
          return ['job', finishedJob.id, 'main'];
        }
      } else if (this.endStatuses.includes(task.status)) {
        const descOrderedJobs = task.jobs.slice().reverse();
        const finishedJob = descOrderedJobs.find(job => this.endStatuses.includes(job.status));
        if (finishedJob) {
          return ['job', finishedJob.id, 'main'];
        }
      }
    }
  }

}
