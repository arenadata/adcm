// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { Component, OnInit, ViewChild } from '@angular/core';
import { MatStepper } from '@angular/material/stepper';
import { ActivatedRoute, Router } from '@angular/router';
import { ClusterService } from '../../core/services/cluster.service';
import { Cluster } from '../../core/types';
import { StepperSelectionEvent } from '@angular/cdk/stepper';

@Component({
  selector: 'app-start',
  templateUrl: './start.component.html',
  styleUrls: ['./start.component.scss'],
})
export class StartComponent implements OnInit {
  cluster: Cluster;
  state = {
    service: false,
    host: false,
    hcm: false,
    config: false,
    actions: false,
  };

  @ViewChild('stepper') stepper: MatStepper;

  constructor(private service: ClusterService, private route: ActivatedRoute, private router: Router) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(p => {
      const id = p.get('id'),
        step = +p.get('step');
      if (id) {
        if (!this.cluster)
          this.service.one_cluster(+id).subscribe(c => {
            this.service.Cluster = c;
            this.cluster = c;
          });

        this.stepper.selectedIndex = step || 1;
      }
    });

    this.stepper.selectionChange.subscribe((a: StepperSelectionEvent) => {
      this.next(a.selectedIndex);
    });
  }

  addCluster(c: Cluster) {
    this.service.Cluster = c;
    this.cluster = c;
    this.next(1);
  }

  next(step: number) {
    this.router.navigate(['wizard', this.cluster.id, step]);
  }
}
