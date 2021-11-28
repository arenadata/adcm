import { ChangeDetectionStrategy, Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { BaseFormDirective } from '../../../shared/add-component';
import { FormArray, FormControl, FormGroup } from '@angular/forms';
import { adwpDefaultProp } from '../../../../../../../adwp_ui/projects/widgets/src/lib/cdk';


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
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RbacRoleComponent<T> extends BaseFormDirective implements OnChanges {

  @Input()
  @adwpDefaultProp()
  value: IRbacRoleView<T> = INITIAL_STATE;

  @Input()
  @adwpDefaultProp()
  options: T[] = [];

  form = new FormGroup({
    name: new FormControl(null),
    description: new FormControl(null),
    child: new FormArray([])
  });

  ngOnChanges(changes: SimpleChanges): void {
    const value = changes['value'];

    if (value) {
      this.form.setValue(value);
    }
  }

  save(): void {
    console.error('RbacRoleComponent | method SAVE not implemented yet  ');
  }

}
