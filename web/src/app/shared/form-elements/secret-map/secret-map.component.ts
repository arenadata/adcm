import { Component, OnInit } from '@angular/core';
import {BaseMapListDirective} from "@app/shared/form-elements/map.component";

@Component({
  selector: 'app-fields-secret-map',
  templateUrl: '../map-list.template.html',
  styleUrls: ['./secret-map.component.scss']
})
export class SecretMapComponent extends BaseMapListDirective implements OnInit {

  ngOnInit(): void {
  }

}
