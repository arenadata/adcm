import {
  Component,
  ElementRef,
  EventEmitter,
  HostBinding,
  Inject,
  Input,
  OnDestroy,
  Optional,
  Output,
  Self,
  ViewEncapsulation
} from '@angular/core';
import { ControlValueAccessor, NgControl } from '@angular/forms';
import {
  ADWP_DEFAULT_STRINGIFY,
  ADWP_IDENTITY_MATCHER,
  adwpAssert,
  adwpDefaultProp,
  AdwpIdentityMatcher,
  AdwpStringHandler
} from '../../../cdk';
import { MAT_FORM_FIELD, MatFormField, MatFormFieldControl } from '@angular/material/form-field';
import { Subject } from 'rxjs';
import { coerceBooleanProperty } from '@angular/cdk/coercion';

@Component({
  selector: 'adwp-select',
  templateUrl: './select.component.html',
  styleUrls: ['./select.component.scss'],
  providers: [{ provide: MatFormFieldControl, useExisting: AdwpSelectComponent }],
  host: {
    'class': 'adwp-select mat-select',
    '[class.mat-select-disabled]': 'disabled',
  },
  encapsulation: ViewEncapsulation.None
})
export class AdwpSelectComponent<T> implements ControlValueAccessor, MatFormFieldControl<any[]>, OnDestroy {

  @Output()
  filter: EventEmitter<string> = new EventEmitter<string>();

  get open(): boolean {
    return this._open;
  }

  set open(value: boolean) {
    if (!this._canOpen()) {
      return;
    }

    this._open = coerceBooleanProperty(value);
  }

  private _open = false;

  controlType = 'adwp-select';

  static nextId = 0;

  @Input()
  options: T[];

  @Input()
  @adwpDefaultProp()
  handler: AdwpStringHandler<T> = ADWP_DEFAULT_STRINGIFY;

  @Input()
  @adwpDefaultProp()
  comparator: AdwpIdentityMatcher<T> = ADWP_IDENTITY_MATCHER;

  @Input()
  @adwpDefaultProp()
  multiple: boolean = true;

  @Input() selectRowDisableCheck: (args: any) => boolean;

  @Input()
  get placeholder() {
    return this._placeholder;
  }

  set placeholder(plh) {
    this._placeholder = plh;
    this.stateChanges.next();
  }

  private _placeholder: string;

  get value(): T[] | null {
    this.stateChanges.next();
    return this._value;
  }

  set value(value: T[] | null) {
    if (this.ngControl) {
      this.onTouched();
      this.ngControl.control.setValue(value);
      this.ngControl.control.markAsDirty();
    }
    this._value = value;
  }

  private _value: T[] | null;

  get empty() {
    return !this._value?.length;
  }

  @Input()
  get required() {
    return this._required;
  }

  set required(req) {
    this._required = coerceBooleanProperty(req);
    this.stateChanges.next();
  }

  private _required = false;

  @Input()
  get disabled(): boolean { return this._disabled; }

  set disabled(value: boolean) {
    this._disabled = coerceBooleanProperty(value);
    this.stateChanges.next();
  }

  private _disabled = false;

  get errorState(): boolean {
    return this.ngControl?.invalid;
  }

  constructor(
    @Optional()
    @Self()
    @Inject(NgControl)
    public readonly ngControl: NgControl | null,
    private _elementRef: ElementRef,
    @Optional() @Inject(MAT_FORM_FIELD) protected _parentFormField: MatFormField,
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


  ngOnDestroy() {
    this.stateChanges.complete();
  }

  triggerHandler: AdwpStringHandler<T[]> = (value): string => {
    if (this.empty) {
      return '';
    }

    return value.map((item) => this.handler(item))?.join(', ');
  };

  readonly autofilled: boolean;

  focused = false;

  onFocusIn(event: FocusEvent): void {
    if (!this.focused && !this.disabled) {
      this.focused = true;
      this.stateChanges.next();
    }
  }

  onFocusOut(event: FocusEvent) {
    if (!this._elementRef.nativeElement.contains(event.relatedTarget as Element)) {
      this.focused = false;
      this.onTouched();
      this.stateChanges.next();
    }
  }

  @HostBinding()
  id = `adwp-select-${AdwpSelectComponent.nextId++}`;

  onContainerClick(event: MouseEvent): void {
    event.stopPropagation();
    this.onFocusIn(event);
    this.open = !this.open;
  }

  setDescribedByIds(ids: string[]): void {
  }

  @HostBinding('class.floating')
  get shouldLabelFloat() {
    return !this.empty;
  }

  stateChanges: any = new Subject<void>();

  // ControlValueAccessor

  protected onChange: (value: any) => void = () => {};
  protected onTouched: () => void = () => {};

  writeValue(value: any[]): void {
    this._value = value;
  }

  registerOnChange(fn: (_: any) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState?(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }

  private _canOpen(): boolean {
    return !this.disabled && this.options?.length > 0;
  }

}
