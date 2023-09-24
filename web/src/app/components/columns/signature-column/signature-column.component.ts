import { Component, Input } from "@angular/core";
import { AdwpCellComponent } from "@app/adwp";

export enum SignatureStatus {
  Valid = 'valid',
  Invalid = 'invalid',
  Absent = 'absent',
}

@Component({
  selector: 'app-signature-column',
  templateUrl: './signature-column.component.html',
  styleUrls: ['./signature-column.component.scss']
})
export class SignatureColumnComponent<T> implements AdwpCellComponent<T> {
  @Input() row: T;
  signatureStatus = SignatureStatus;

  firstCharToUpperCase(string){
    return string[0].toUpperCase() + string.slice(1).toLowerCase();
  }
}
