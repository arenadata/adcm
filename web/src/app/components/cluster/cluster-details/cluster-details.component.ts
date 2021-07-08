import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { map } from 'rxjs/operators';

import { DetailsDirective } from '@app/abstract-directives/details.directive';
import { ApiService } from '../../../core/api';
import { EntityHelper } from '../../../helpers/entity-helper';
import { AdcmTypedEntity } from '../../../models/entity';
import { NavItem } from '../../../shared/details/navigation.service';

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
    },
    {
      title: 'Configuration',
      url: 'config',
    },
    {
      title: 'Status',
      url: 'status',
    },
    {
      title: 'Import',
      url: 'import',
    },
    {
      title: 'Actions',
      url: 'action',
    },
    {
      title: 'Services',
      url: 'service',
    },
    {
      title: 'Hosts',
      url: 'host',
    },
    {
      title: 'Hosts - Components',
      url: 'host-component',
    }
  ];

  constructor(
    private api: ApiService,
    private route: ActivatedRoute,
  ) {
    super();
  }

  ngOnInit() {
    this.route.params.pipe(this.takeUntil()).subscribe((params) => {
      this.path = EntityHelper.entityToTypedEntity(
        this.api.getOne<any>('cluster', params.cluster),
        'cluster',
      ).pipe(map((cluster: AdcmTypedEntity) => [cluster]));
    });
  }

}
