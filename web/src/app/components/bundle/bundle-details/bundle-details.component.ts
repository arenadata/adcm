import { Component, Injector } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';

import { DetailsFactory } from '@app/factories/details.factory';
import { DetailAbstractDirective } from '@app/abstract-directives/detail.abstract.directive';
import { Bundle } from '@app/core/types';
import { SocketState } from '@app/core/store';
import { ClusterService } from '@app/core/services/cluster.service';
import { ChannelService } from '@app/core/services';
import { BundleService } from '@app/services/bundle.service';

@Component({
  selector: 'app-bundle-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['../../../styles/details.scss']
})
export class BundleDetailsComponent extends DetailAbstractDirective<Bundle> {

  entityParam = 'bundle';

  leftMenu = [
    DetailsFactory.labelMenuItem('Main', 'main'),
    DetailsFactory.labelMenuItem('License', 'license'),
  ];

  constructor(
    socket: Store<SocketState>,
    protected route: ActivatedRoute,
    protected service: ClusterService,
    protected channel: ChannelService,
    protected store: Store,
    injector: Injector,
    protected subjectService: BundleService,
  ) {
    super(socket, route, service, channel, store, injector);
  }

}
