import { Component } from '@angular/core';
import { DetailsDirective } from '@app/abstract-directives/details.directive';

@Component({
  selector: 'app-cluster-details',
  templateUrl: './cluster-details.component.html',
  styleUrls: ['./cluster-details.component.scss']
})
export class ClusterDetailsComponent extends DetailsDirective {

  constructor() {
    super();
  }

}
