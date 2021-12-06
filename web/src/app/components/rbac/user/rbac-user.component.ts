import { ChangeDetectionStrategy, Component, Input, OnInit } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { clearEmptyField } from '../../../core/types';
import { take } from 'rxjs/operators';
import { ADD_SERVICE_PROVIDER } from '../../../shared/add-component/add-service-model';
import { RbacUserService } from './rbac-user.service';
import { RbacUserModel } from '../../../models/rbac/rbac-user.model';
import { BaseFormDirective } from '../../../shared/add-component';

@Component({
  selector: 'app-rbac-user',
  templateUrl: './rbac-user.component.html',
  styleUrls: ['./rbac-user.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: RbacUserService }
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RbacUserComponent<T> extends BaseFormDirective implements OnInit {

  @Input()
  value: RbacUserModel;

  get title() {
    return this.value ? 'Update' : 'Create';
  }

  form = new FormGroup({
    id: new FormControl(null),
    is_superuser: new FormControl(null),
    url: new FormControl(null),
    profile: new FormControl(null),
    username: new FormControl(null),
    password: new FormControl(null, [Validators.required, Validators.pattern('[a-zA-Z0-9]*')]),
    first_name: new FormControl(null),
    last_name: new FormControl(null),
    email: new FormControl(null),
    group: new FormControl([])
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
