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
import { ConcernEventType } from '@app/models/concern/concern-reason';

@Component({
  selector: 'app-cluster-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['../../../styles/details.scss']
})
export class ClusterDetailsComponent extends DetailAbstractDirective<ICluster> {

  entityParam = 'cluster';

  leftMenu = [
    DetailsFactory.labelMenuItem('Main', 'main'),
    DetailsFactory.concernMenuItem('Services', 'service', 'service', ConcernEventType.Cluster, 'cluster'),
    DetailsFactory.labelMenuItem('Hosts', 'host'),
    DetailsFactory.concernMenuItem('Hosts - Components', 'host_component', 'host-component', ConcernEventType.Cluster, 'cluster'),
    DetailsFactory.concernMenuItem('Configuration', 'config', 'config', ConcernEventType.Cluster, 'cluster'),
    DetailsFactory.labelMenuItem('Configuration groups', 'group_config'),
    DetailsFactory.statusMenuItem('Status', 'status', 'cluster'),
    DetailsFactory.concernMenuItem('Import', 'import', 'import', ConcernEventType.Cluster, 'cluster'),
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
