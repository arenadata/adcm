import { Component, Injector } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';

import { DetailsFactory } from '@app/factories/details.factory';
import { IHost } from '@app/models/host';
import { SocketState } from '@app/core/store';
import { ClusterService } from '@app/core/services/cluster.service';
import { ChannelService } from '@app/core/services';
import { HostService } from '@app/services/host.service';
import { DetailAbstractDirective } from '@app/abstract-directives/detail.abstract.directive';

@Component({
  selector: 'app-host-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['../../../styles/details.scss']
})
export class HostDetailsComponent extends DetailAbstractDirective<IHost> {

  entityParam = 'host';

  leftMenu = [
    DetailsFactory.labelMenuItem('Main', 'main'),
    DetailsFactory.labelMenuItem('Configuration', 'config'),
    DetailsFactory.statusMenuItem('Status', 'status', 'host'),
  ];

  constructor(
    socket: Store<SocketState>,
    protected route: ActivatedRoute,
    protected service: ClusterService,
    protected channel: ChannelService,
    protected store: Store,
    injector: Injector,
    protected subjectService: HostService,
  ) {
    super(socket, route, service, channel, store, injector);
  }

}
