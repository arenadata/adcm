import { Component, Injector } from '@angular/core';
import { Store } from '@ngrx/store';

import { DetailsFactory } from '@app/factories/details.factory';
import { DetailAbstractDirective } from '@app/abstract-directives/detail.abstract.directive';
import { SocketState } from '@app/core/store';
import { ActivatedRoute } from '@angular/router';
import { ClusterService } from '@app/core/services/cluster.service';
import { ChannelService } from '@app/core/services';
import { GroupConfigService } from '@app/services/group-config.service';
import { ConfigGroup } from '@app/config-groups';

@Component({
  selector: 'app-group-config-provider-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['./../../../shared/details/detail.component.scss']
})
export class GroupConfigDetailsComponent extends DetailAbstractDirective<ConfigGroup> {

  leftMenu = [
    DetailsFactory.labelMenuItem('Hosts', 'host'),
    DetailsFactory.labelMenuItem('Configuration', 'config'),
  ];

  constructor(
    socket: Store<SocketState>,
    protected route: ActivatedRoute,
    protected service: ClusterService,
    protected channel: ChannelService,
    protected store: Store,
    injector: Injector,
    protected subjectService: GroupConfigService,
  ) {
    super(socket, route, service, channel, store, injector);
  }

}
