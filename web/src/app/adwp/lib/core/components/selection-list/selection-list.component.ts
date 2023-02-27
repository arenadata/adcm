import {
  AfterViewInit,
  Component,
  EventEmitter,
  Inject,
  Input,
  Optional,
  Output,
  QueryList,
  Self,
  ViewChild
} from '@angular/core';
import {
  ADWP_DEFAULT_MATCHER,
  ADWP_DEFAULT_STRINGIFY,
  ADWP_IDENTITY_MATCHER,
  adwpAssert,
  adwpDefaultProp,
  AdwpIdentityMatcher,
  AdwpMatcher,
  AdwpStringHandler,
  concatBy,
  difference
} from '../../../cdk';
import { ControlValueAccessor, NgControl } from '@angular/forms';
import { MatListOption, MatSelectionList, MatSelectionListChange } from '@angular/material/list';

@Component({
  selector: 'adwp-selection-list',
  templateUrl: './selection-list.component.html',
  styleUrls: ['./selection-list.component.css'],
})
export class AdwpSelectionListComponent<T> implements ControlValueAccessor, AfterViewInit {

  public readonly matcher: AdwpMatcher<T> = ADWP_DEFAULT_MATCHER;

  @ViewChild('selectionList', { static: false }) list: MatSelectionList;

  @Input()
  @adwpDefaultProp()
  options: T[] = [];

  @Input()
  @adwpDefaultProp()
  handler: AdwpStringHandler<T> = ADWP_DEFAULT_STRINGIFY;

  @Input()
  @adwpDefaultProp()
  multiple: boolean = true;

  @Input() selectRowDisableCheck: (args: any) => boolean;

  @Output()
  filter: EventEmitter<string> = new EventEmitter<string>();

  @Input()
  @adwpDefaultProp()
  comparator: AdwpIdentityMatcher<T> = ADWP_IDENTITY_MATCHER;

  get value(): any[] | null {
    return this._value;
  }

  set value(value: any[] | null) {
    if (this.ngControl) {
      this.ngControl.control.setValue(value);
    }
    this._value = value;
  }

  private _value: any[] | null;

  constructor(
    @Optional()
    @Self()
    @Inject(NgControl)
    public readonly ngControl: NgControl | null
  ) {
    if (ngControl === null) {
      adwpAssert.assert(
        false,
        `NgControl not injected in ${this.constructor.name}!\n`,
        'Use [(ngModel)] or [formControl] or formControlName for correct work.',
      );
    } else {
      ngControl.valueAccessor = this;
    }
  }

  ngAfterViewInit(): void {
    /**
     * When changing the list with options (for example, after filtering),
     * we need to restore the "selected" state.
     * To do this, we look at "this.value" and set the checkbox.
     */
    this.list.options.changes.subscribe((list: QueryList<MatListOption>) => {
      const matOptions = list.toArray();
      matOptions.forEach((option) => {
        if (this.value.some((i) => i.id === option.value.id)) {
          option._setSelected(true);
        }
      });
    });
  }

  updateValue(event: MatSelectionListChange): void {
    const option = event.options[0];
    const values = event.options.map(o => o.value);

    const isAppend = option.selected;
    if (isAppend) {
      this.value = concatBy(this.value, values, this.comparator);
    } else {
      this.value = difference(this.value, values, this.comparator);
    }
  }

  // ControlValueAccessor

  protected onChange: (value: any) => void = () => {};

  protected onTouched: () => void = () => {};

  writeValue(value: T[]): void {
    this._value = value;
  }

  registerOnChange(fn: (_: T) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState?(isDisabled: boolean): void {

  }
}
