import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { AdwpIdentityMatcher, AdwpStringHandler } from '../../cdk';

@Component({
  selector: 'adwp-input-select',
  templateUrl: './input-select.component.html',
  styleUrls: ['./input-select.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AdwpInputSelectComponent<T> {

  @Input() form: FormGroup;

  @Input() controlName: string;

  @Input() options: T[];

  @Input() multiple: boolean;

  @Input() label: string;

  @Input() handler: AdwpStringHandler<T>;

  @Input() comparator: AdwpIdentityMatcher<T>;

  @Input() isRequired = false;

  @Input() selectRowDisableCheck: (args: any) => boolean;

  @Output() filter: EventEmitter<string> = new EventEmitter<string>();

  isError(name: string): boolean {
    const f = this.form.get(name);
    return f.invalid && (f.dirty || f.touched);
  }

  hasError(name: string, error: string): boolean {
    return this.form.controls[name].hasError(error);
  }
}
