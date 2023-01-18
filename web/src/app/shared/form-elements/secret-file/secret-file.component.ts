import { Component, OnInit } from '@angular/core';
import { SecretTextComponent } from "@app/shared/form-elements/secret-text/secret-text.component";

@Component({
  selector: 'app-fields-secret-file',
  templateUrl: './secret-file.component.html',
  styleUrls: ['./secret-file.component.scss']
})
export class SecretFileComponent extends SecretTextComponent implements OnInit {

  constructor() {
    super();
  }

  ngOnInit(): void {
  }

}
