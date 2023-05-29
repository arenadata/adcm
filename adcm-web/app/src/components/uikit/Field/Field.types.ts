export type FieldVariant = 'primary' | 'secondary';
export interface FieldProps {
  variant?: FieldVariant;
  disabled?: boolean;
  hasError?: boolean;
}
