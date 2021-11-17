import { Component, Injector } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';

import { DetailsFactory } from '@app/factories/details.factory';
import { DetailAbstractDirective } from '@app/abstract-directives/detail.abstract.directive';
import { Provider } from '@app/core/types';
import { SocketState } from '@app/core/store';
import { ClusterService } from '@app/core/services/cluster.service';
import { ChannelService } from '@app/core/services';
import { ProviderService } from '@app/services/provider.service';
import { ConcernEventType } from '@app/models/concern/concern-reason';

@Component({
  selector: 'app-provider-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['../../../styles/details.scss']
})
export class ProviderDetailsComponent extends DetailAbstractDirective<Provider> {

  entityParam = 'provider';

  leftMenu = [
    DetailsFactory.labelMenuItem('Main', 'main'),
    DetailsFactory.concernMenuItem('Configuration', 'config', 'config', ConcernEventType.HostProvider, 'provider'),
    DetailsFactory.labelMenuItem('Configuration groups', 'group_config'),
  ];

  constructor(
    socket: Store<SocketState>,
    protected route: ActivatedRoute,
    protected service: ClusterService,
    protected channel: ChannelService,
    protected store: Store,
    injector: Injector,
    protected subjectService: ProviderService,
  ) {
    super(socket, route, service, channel, store, injector);
  }

}
