import { Component, Injector } from '@angular/core';
import { ActivatedRoute, ParamMap } from '@angular/router';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';

import { DetailsFactory } from '@app/factories/details.factory';
import { DetailAbstractDirective } from '@app/abstract-directives/detail.abstract.directive';
import { SocketState } from '@app/core/store';
import { ClusterService, WorkerInstance } from '@app/core/services/cluster.service';
import { ChannelService } from '@app/core/services';
import { ConfigGroup, ConfigGroupListService } from '@app/config-groups';

@Component({
  selector: 'app-group-config-provider-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['../../../styles/details.scss']
})
export class GroupConfigDetailsComponent extends DetailAbstractDirective<ConfigGroup> {

  entityParam = 'group_config';

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
    protected subjectService: ConfigGroupListService,
  ) {
    super(socket, route, service, channel, store, injector);
  }

  initContext(param: ParamMap): Observable<WorkerInstance> {
    return this.service.getContext(param, this.subjectService);
  }

}
