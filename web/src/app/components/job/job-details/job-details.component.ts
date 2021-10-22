import { Component, Injector } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';

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

  leftMenu = [
    DetailsFactory.labelMenuItem('Main', 'main'),
  ];

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

}
