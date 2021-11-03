import { Component, Injector } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';

import { DetailsFactory } from '@app/factories/details.factory';
import { DetailAbstractDirective } from '@app/abstract-directives/detail.abstract.directive';
import { ICluster } from '@app/models/cluster';
import { SocketState } from '@app/core/store';
import { ClusterService } from '@app/core/services/cluster.service';
import { ChannelService } from '@app/core/services';
import { ClusterEntityService } from '@app/services/cluster-entity.service';

@Component({
  selector: 'app-cluster-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['../../../styles/details.scss']
})
export class ClusterDetailsComponent extends DetailAbstractDirective<ICluster> {

  entityParam = 'cluster';

  leftMenu = [
    DetailsFactory.labelMenuItem('Main', 'main'),
    DetailsFactory.labelMenuItem('Services', 'service'),
    DetailsFactory.labelMenuItem('Hosts', 'host'),
    DetailsFactory.labelMenuItem('Hosts - Components', 'host_component'),
    DetailsFactory.labelMenuItem('Configuration', 'config'),
    DetailsFactory.labelMenuItem('Configuration groups', 'group_config'),
    DetailsFactory.statusMenuItem('Status', 'status', 'cluster'),
    DetailsFactory.labelMenuItem('Import', 'import'),
  ];

  constructor(
    socket: Store<SocketState>,
    protected route: ActivatedRoute,
    protected service: ClusterService,
    protected channel: ChannelService,
    protected store: Store,
    injector: Injector,
    protected subjectService: ClusterEntityService,
  ) {
    super(socket, route, service, channel, store, injector);
  }

}
