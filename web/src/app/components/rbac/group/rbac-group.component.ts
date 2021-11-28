import { ChangeDetectionStrategy, Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { BaseFormDirective } from '../../../shared/add-component';
import { FormArray, FormControl, FormGroup } from '@angular/forms';
import { adwpDefaultProp } from '../../../../../../../adwp_ui/projects/widgets/src/lib/cdk';


interface IRbacGroupView<T> {
  name: string | null;
  description: string | null;
  users: T[];
}

const INITIAL_STATE: IRbacGroupView<any> = {
  name: '',
  description: '',
  users: []
};


@Component({
  selector: 'app-rbac-group',
  templateUrl: './rbac-group.component.html',
  styleUrls: ['./rbac-group.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RbacGroupComponent<T> extends BaseFormDirective implements OnChanges {

  @Input()
  @adwpDefaultProp()
  value: IRbacGroupView<T> = INITIAL_STATE;

  @Input()
  @adwpDefaultProp()
  options: T[] = [];

  form = new FormGroup({
    name: new FormControl(null),
    description: new FormControl(null),
    users: new FormArray([])
  });

  ngOnChanges(changes: SimpleChanges): void {
    const value = changes['value'];

    if (value) {
      this.form.setValue(value);
    }
  }

  save(): void {
    console.error('RbacGroupComponent | method SAVE not implemented yet  ');
  }

}
