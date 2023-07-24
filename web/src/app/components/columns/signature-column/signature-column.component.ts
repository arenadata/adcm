import { Component, Input } from "@angular/core";
import { AdwpCellComponent } from "@app/adwp";

@Component({
  selector: 'app-signature-column',
  templateUrl: './signature-column.component.html',
  styleUrls: ['./signature-column.component.scss']
})
export class SignatureColumnComponent<T> implements AdwpCellComponent<T> {
  @Input() row: T;
}
