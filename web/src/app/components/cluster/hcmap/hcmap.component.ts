import { Component, OnInit } from '@angular/core';

import { ClusterService } from '@app/core/services/cluster.service';

@Component({
  template: ` <app-service-host [cluster]="cluster"></app-service-host> `,
  styles: [':host { flex: 1; }'],
})
export class HcmapComponent implements OnInit {
  cluster: { id: number; hostcomponent: string };
  constructor(private service: ClusterService) {}

  ngOnInit() {
    const { id, hostcomponent } = { ...this.service.Cluster };
    this.cluster = { id, hostcomponent };
  }
}
