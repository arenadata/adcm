import { ChangeDetectionStrategy, Component, Input, SimpleChanges } from '@angular/core';
import { BaseFormDirective } from '../../../shared/add-component';
import { adwpDefaultProp } from '../../../../../../../adwp_ui/projects/widgets/src/lib/cdk';
import { FormArray, FormControl, FormGroup } from '@angular/forms';

interface IRbacUserView<T> {
  userName: string | null;
  password: string | null;
  firstName: string | null;
  lastName: string | null;
  email: string | null;
  groups: T[];
}

const INITIAL_STATE: IRbacUserView<any> = {
  userName: '',
  password: '',
  firstName: '',
  lastName: '',
  email: '',
  groups: [],
};

@Component({
  selector: 'app-rbac-user',
  templateUrl: './rbac-user.component.html',
  styleUrls: ['./rbac-user.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RbacUserComponent<T> extends BaseFormDirective {

  @Input()
  @adwpDefaultProp()
  value: IRbacUserView<T> = INITIAL_STATE;

  @Input()
  @adwpDefaultProp()
  options: T[] = [];

  form = new FormGroup({
    userName: new FormControl(null),
    password: new FormControl(null),
    firstName: new FormControl(null),
    lastName: new FormControl(null),
    email: new FormControl(null),
    groups: new FormArray([])
  });

  ngOnChanges(changes: SimpleChanges): void {
    const value = changes['value'];

    if (value) {
      this.form.setValue(value);
    }
  }

  save(): void {
    console.error('RbacUserComponent | method SAVE not implemented yet  ');
  }

}
