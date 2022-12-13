import { Component } from '@angular/core';
import { BaseMapListDirective } from "@app/shared/form-elements/map.component";

@Component({
  selector: 'app-fields-secret-map',
  templateUrl: '../map-list.template.html',
  styleUrls: ['../map.component.scss', './secret-map.component.scss']
})
export class SecretMapComponent extends BaseMapListDirective {
  asList = false;
}
