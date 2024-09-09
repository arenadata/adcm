import { FieldProps } from '@uikit';
import s from './TextFormField.module.scss';

export interface TextFormField extends FieldProps, React.PropsWithChildren {}

const TextFormField = ({ children }: TextFormField) => <div className={s.TextFormField}>{children}</div>;

export default TextFormField;
