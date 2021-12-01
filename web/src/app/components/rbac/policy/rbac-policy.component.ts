import { ChangeDetectionStrategy, Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { BaseFormDirective } from '../../../shared/add-component';
import { AbstractControl, FormArray, FormControl, FormGroup, Validators } from '@angular/forms';
import { adwpDefaultProp } from '../../../../../../../adwp_ui/projects/widgets/src/lib/cdk';


interface IRbacPolicyView<T> {
  name: string | null;
  description: string | null;
  object: unknown;
  role: unknown;
  user: unknown[];
  group: unknown[];
}

const INITIAL_STATE: IRbacPolicyView<any> = {
  name: '',
  description: '',
  object: '',
  role: '',
  user: [],
  group: []
};


@Component({
  selector: 'app-rbac-policy',
  templateUrl: './rbac-policy.component.html',
  styleUrls: ['./rbac-policy.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RbacPolicyComponent<T> extends BaseFormDirective implements OnChanges {

  @Input()
  @adwpDefaultProp()
  value: IRbacPolicyView<T> = INITIAL_STATE;

  @Input()
  @adwpDefaultProp()
  options: T[] = [];

  /** Returns a FormArray with the name 'steps'. */
  get steps(): AbstractControl | null { return this.form.get('steps'); }

  form = new FormGroup({
    steps: new FormArray([
      new FormGroup({
        name: new FormControl(null, [Validators.required]),
        description: new FormControl(null),
        role: new FormControl(null),
        user: new FormArray([]),
        group: new FormArray([])
      }),
      new FormGroup({
        object: new FormControl(null)
      })
    ])
  });


  ngOnChanges(changes: SimpleChanges): void {
    const value = changes['value'];

    if (value) {
      this.form.setValue(value);
    }
  }

  save(): void {
    console.error('RbacPolicyComponent | method SAVE not implemented yet  ');
  }

  step(id: number): FormGroup | null {
    return this.steps.get([id]) as FormGroup;
  }

}
