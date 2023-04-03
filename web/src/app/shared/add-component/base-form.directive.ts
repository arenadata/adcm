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
import { Directive, Inject } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { BaseDirective } from '@app/adwp';

import { ADD_SERVICE_PROVIDER, IAddService } from '@app/shared/add-component/add-service-model';
import { ApiService } from "@app/core/api";

@Directive({
  selector: '[appBaseForm]',
})
export class BaseFormDirective extends BaseDirective {
  form = new FormGroup({});

  constructor(
    @Inject(ADD_SERVICE_PROVIDER) public service: IAddService,
    public dialog: MatDialog,
    public api?: ApiService
  ) {
    super();
  }

  onCancel(): void {
    this.form.reset();
    this.dialog.closeAll();
  }

  save() {}
}
