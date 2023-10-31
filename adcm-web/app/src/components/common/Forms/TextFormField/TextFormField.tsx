import { FieldProps } from '@uikit';
import s from './TextFromField.module.scss';

export interface TextFormField extends FieldProps, React.PropsWithChildren {}

const TextFromField = ({ children }: TextFormField) => <div className={s.textFromField}>{children}</div>;

export default TextFromField;
