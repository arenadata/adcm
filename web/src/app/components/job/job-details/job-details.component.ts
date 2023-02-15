import { Component, Injector } from '@angular/core';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { Store } from '@ngrx/store';
import { filter, switchMap } from 'rxjs/operators';
import { Subscription } from 'rxjs';

import { Job } from '@app/core/types';
import { DetailsFactory } from '@app/factories/details.factory';
import { SocketState } from '@app/core/store';
import { ClusterService } from '@app/core/services/cluster.service';
import { ChannelService } from '@app/core/services';
import { JobService } from '@app/services/job.service';
import { DetailAbstractDirective } from '@app/abstract-directives/detail.abstract.directive';

@Component({
  selector: 'app-job-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['../../../styles/details.scss']
})
export class JobDetailsComponent extends DetailAbstractDirective<Job> {

  entityParam = 'job';

  leftMenu = [];

  jobEvents$: Subscription;

  constructor(
    socket: Store<SocketState>,
    protected route: ActivatedRoute,
    protected service: ClusterService,
    protected channel: ChannelService,
    protected store: Store,
    injector: Injector,
    protected subjectService: JobService,
  ) {
    super(socket, route, service, channel, store, injector);
  }

  prepareMenuItems() {
    const itemsOfFiles = this.entity.log_files.map(
      (file) => DetailsFactory.logMenuItem(`${file.name} [ ${file.type} ]`, file.id.toString(), file.id)
    );

    this.leftMenu = [
      DetailsFactory.labelMenuItem('Main', 'main'),
      ...itemsOfFiles,
    ];
  }

  entityReceived(entity: Job) {
    super.entityReceived(entity);

    this.currentName = entity.display_name;
    this.prepareMenuItems();

    if (this.jobEvents$) {
      this.jobEvents$.unsubscribe();
    }

    this.jobEvents$ = this.subjectService.events({
      events: ['change_job_status', 'add_job_log'],
    }).pipe(
      this.takeUntil(),
      filter(event => event?.object?.id === this.entity.id),
      switchMap(() => this.subjectService.get(this.entity.id)),
    ).subscribe((resp) => {
      const param = convertToParamMap({job: resp.id});
      this.entity = resp;

      this.initContext(param);
      this.prepareMenuItems();
    });
  }

}
