import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { map } from 'rxjs/operators';
import { Store } from '@ngrx/store';

import { DetailsDirective } from '@app/abstract-directives/details.directive';
import { ApiService } from '@app/core/api';
import { EntityHelper } from '@app/helpers/entity-helper';
import { AdcmTypedEntity } from '@app/models/entity';
import { NavItem } from '@app/shared/details/navigation.service';
import { SocketState } from '@app/core/store';
import { ClusterService } from '@app/core/services/cluster.service';
import { ChannelService } from '@app/core/services';

@Component({
  selector: 'app-cluster-details',
  templateUrl: './cluster-details.component.html',
  styleUrls: ['./cluster-details.component.scss']
})
export class ClusterDetailsComponent extends DetailsDirective implements OnInit {

  title = '';

  items: NavItem[] = [
    {
      title: 'Main',
      url: 'main',
    }, {
      title: 'Services',
      url: 'service',
    }, {
      title: 'Hosts',
      url: 'host',
    }, {
      title: 'Hosts - Components',
      url: 'host-component',
    }, {
      title: 'Configuration',
      url: 'config',
    }, {
      title: 'Status',
      url: 'status',
    }, {
      title: 'Import',
      url: 'import',
    }, {
      title: 'Actions',
      url: 'action',
    },
  ];

  constructor(
    protected socket: Store<SocketState>,
    protected route: ActivatedRoute,
    protected service: ClusterService,
    protected channel: ChannelService,
    protected store: Store,
    private api: ApiService,
  ) {
    super(socket, route, service, channel, store);
  }

  ngOnInit() {
    super.ngOnInit();

    this.route.params.pipe(this.takeUntil()).subscribe((params) => {
      this.path = EntityHelper.entityToTypedEntity(
        this.api.getOne<any>('cluster', params.cluster),
        'cluster',
      ).pipe(map((cluster: AdcmTypedEntity) => [cluster]));
    });
  }

}
