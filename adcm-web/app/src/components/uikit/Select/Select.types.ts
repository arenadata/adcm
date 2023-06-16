export type SelectValue = string | number | null;

export interface SelectOption<T = SelectValue> {
  value: T;
  label: string;
  disabled?: boolean;
}

export interface SingleSelectParams<T> {
  options: SelectOption<T>[];
  value: T | null;
  onChange: (_value: T | null) => void;
}

export interface SingleSelectOptions<T> extends SingleSelectParams<T> {
  noneLabel?: string;
  maxHeight?: number;
  isSearchable?: boolean;
  searchPlaceholder?: string;
}

export interface MultiPropsParams<T> {
  options: SelectOption<T>[];
  value: T[];
  onChange: (_value: T[]) => void;
}
