export type SelectValue = string | number | null;

export interface SelectOption<T = SelectValue> {
  value: T;
  label: string;
  disabled?: boolean;
}

export interface SingleSelectParams<T> {
  options: SelectOption<T>[];
  value: T | null;
  onChange: (value: T | null) => void;
}

interface CommonSelectParams {
  maxHeight?: number;
  isSearchable?: boolean;
  searchPlaceholder?: string;
}

export interface SingleSelectOptions<T> extends SingleSelectParams<T>, CommonSelectParams {
  noneLabel?: string;
}

export interface MultiPropsParams<T> {
  options: SelectOption<T>[];
  value: T[];
  onChange: (value: T[]) => void;
}

export interface MultiSelectOptions<T> extends MultiPropsParams<T>, CommonSelectParams {
  checkAllLabel?: string;
}
