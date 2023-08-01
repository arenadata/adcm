import { FieldProps } from '@uikit';

export interface TextFormField extends FieldProps, React.PropsWithChildren {}

const TextFromField = ({ children }: TextFormField) => <span>{children}</span>;

export default TextFromField;
