import { ChangeDetectionStrategy, Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { BaseFormDirective } from '../../../shared/add-component';
import { FormControl, FormGroup } from '@angular/forms';
import { clearEmptyField } from '../../../core/types';
import { take } from 'rxjs/operators';


interface IRbacRoleView<T> {
  name: string | null;
  description: string | null;
  child: T[];
}

const INITIAL_STATE: IRbacRoleView<any> = {
  name: '',
  description: '',
  child: []
};


@Component({
  selector: 'app-rbac-role',
  templateUrl: './rbac-role.component.html',
  styleUrls: ['./rbac-role.component.scss'],
  // providers: [
  //   { provide: ADD_SERVICE_PROVIDER, useExisting: RbacRoleService }
  // ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RbacRoleComponent<T> extends BaseFormDirective implements OnChanges {

  @Input()
  value: IRbacRoleView<T> = INITIAL_STATE;

  @Input()
  options: T[] = [];

  parametrizedOptions: ('Cluster' | 'Service' | 'Component' | 'Provider' | 'Host')[] = [
    'Cluster',
    'Service',
    'Component',
    'Provider',
    'Host',
  ];

  form = new FormGroup({
    name: new FormControl(null),
    description: new FormControl(null),
    category: new FormControl(['adcm']),
    parametrized_by_type: new FormControl([]),
    child: new FormControl([])
  });

  ngOnChanges(changes: SimpleChanges): void {
    const value = changes['value'];

    if (value) {
      this.form.setValue(value);
    }
  }

  save(): void {
    const data = clearEmptyField(this.form.value);

    this.service
      .add(data)
      .pipe(take(1))
      .subscribe((_) => this.onCancel());
  }

}
