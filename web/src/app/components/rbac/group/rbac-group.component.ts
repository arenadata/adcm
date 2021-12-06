import { ChangeDetectionStrategy, Component, Input, OnInit } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { take } from 'rxjs/operators';
import { clearEmptyField } from '../../../core/types';
import { RbacGroupModel } from '../../../models/rbac/rbac-group.model';
import { ADD_SERVICE_PROVIDER } from '../../../shared/add-component/add-service-model';
import { RbacGroupService } from './rbac-group.service';
import { BaseFormDirective } from '../../../shared/add-component';


@Component({
  selector: 'app-rbac-group',
  templateUrl: './rbac-group.component.html',
  styleUrls: ['./rbac-group.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: RbacGroupService }
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RbacGroupComponent<T> extends BaseFormDirective implements OnInit {

  @Input()
  value: RbacGroupModel;

  get title() {
    return this.value ? 'Update' : 'Create';
  }

  form = new FormGroup({
    id: new FormControl(null),
    name: new FormControl(null),
    description: new FormControl(null),
    user: new FormControl([]),
    url: new FormControl(null),
  });

  ngOnInit(): void {
    if (this.value) {
      this.form.setValue(this.value);
    }
  }

  save(): void {
    const data = clearEmptyField(this.form.value);

    if (this.value) {
      this.service
        .update(this.value.url, data)
        .pipe(take(1))
        .subscribe((_) => this.onCancel());
    } else {
      this.service
        .add(data)
        .pipe(take(1))
        .subscribe((_) => this.onCancel());
    }
  }

}
