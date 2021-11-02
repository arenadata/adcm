import { Component, Injector } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';

import { DetailAbstractDirective } from '@app/abstract-directives/detail.abstract.directive';
import { Service } from '@app/core/types';
import { SocketState } from '@app/core/store';
import { ClusterService } from '@app/core/services/cluster.service';
import { ChannelService } from '@app/core/services';
import { ServiceService } from '@app/services/service.service';
import { DetailsFactory } from '@app/factories/details.factory';

@Component({
  selector: 'app-service-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['../../../styles/details.scss']
})
export class ServiceDetailsComponent extends DetailAbstractDirective<Service> {

  entityParam = 'service';

  leftMenu = [
    DetailsFactory.labelMenuItem('Main', 'main'),
    DetailsFactory.labelMenuItem('Components', 'component'),
    DetailsFactory.labelMenuItem('Configuration', 'config'),
    DetailsFactory.labelMenuItem('Configuration groups', 'group_config'),
    DetailsFactory.statusMenuItem('Status', 'status', 'service'),
    DetailsFactory.labelMenuItem('Import', 'import'),
  ];

  constructor(
    socket: Store<SocketState>,
    protected route: ActivatedRoute,
    protected service: ClusterService,
    protected channel: ChannelService,
    protected store: Store,
    injector: Injector,
    protected subjectService: ServiceService,
  ) {
    super(socket, route, service, channel, store, injector);
  }

}
