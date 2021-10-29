import { Component, Injector } from '@angular/core';
import { Store } from '@ngrx/store';
import { ActivatedRoute } from '@angular/router';

import { DetailAbstractDirective } from '@app/abstract-directives/detail.abstract.directive';
import { SocketState } from '@app/core/store';
import { ClusterService } from '@app/core/services/cluster.service';
import { ChannelService } from '@app/core/services';
import { ServiceComponentService } from '@app/services/service-component.service';
import { DetailsFactory } from '@app/factories/details.factory';
import { IServiceComponent } from '@app/models/service-component';

@Component({
  selector: 'app-service-component-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['../../../styles/details.scss']
})
export class ServiceComponentDetailsComponent extends DetailAbstractDirective<IServiceComponent> {

  entityParam = 'servicecomponent';

  leftMenu = [
    DetailsFactory.labelMenuItem('Main', 'main'),
    DetailsFactory.labelMenuItem('Configuration', 'config'),
    DetailsFactory.labelMenuItem('Configuration groups', 'group_config'),
    DetailsFactory.statusMenuItem('Status', 'status', 'component'),
  ];

  constructor(
    socket: Store<SocketState>,
    protected route: ActivatedRoute,
    protected service: ClusterService,
    protected channel: ChannelService,
    protected store: Store,
    injector: Injector,
    protected subjectService: ServiceComponentService,
  ) {
    super(socket, route, service, channel, store, injector);
  }

}
