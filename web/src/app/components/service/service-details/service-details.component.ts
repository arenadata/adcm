import { Component, Injector } from '@angular/core';
import { Store } from '@ngrx/store';

import { DetailAbstractDirective } from '@app/abstract-directives/detail.abstract.directive';
import { Service } from '@app/core/types';
import { SocketState } from '@app/core/store';
import { ActivatedRoute } from '@angular/router';
import { ClusterService } from '@app/core/services/cluster.service';
import { ChannelService } from '@app/core/services';
import { ServiceService } from '@app/services/service.service';
import { DetailsFactory } from '@app/factories/details.factory';

@Component({
  selector: 'app-service-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['./../../../shared/details/detail.component.scss']
})
export class ServiceDetailsComponent extends DetailAbstractDirective<Service> {

  leftMenu = [
    DetailsFactory.labelMenuItem('Main', 'main'),
    DetailsFactory.labelMenuItem('Configuration', 'config'),
    DetailsFactory.labelMenuItem('Configuration groups', 'group_config'),
    DetailsFactory.statusMenuItem('Status', 'status'),
    DetailsFactory.labelMenuItem('Import', 'import'),
    DetailsFactory.labelMenuItem('Components', 'component'),
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
