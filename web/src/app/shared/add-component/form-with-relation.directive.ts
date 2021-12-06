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
import { MatDialog } from '@angular/material/dialog';

import { ADD_SERVICE_PROVIDER, IAddService } from '@app/shared/add-component/add-service-model';
import { BaseFormDirective } from './base-form.directive';

@Directive({
  selector: '[appRelationForm]',
})
export class FormWithRelationDirective<T extends IAddService = IAddService> extends BaseFormDirective {
  value: any;

  constructor(
    @Inject(ADD_SERVICE_PROVIDER) public service: T,
    public dialog: MatDialog,
  ) {
    super(service, dialog);
  }

  onCancel(): void {
    this.form.reset();
    this.dialog.closeAll();
  }

  save() {}

}
