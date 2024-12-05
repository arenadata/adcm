import type { FieldErrors } from '@models/adcm';
import s from './FieldNodeErrors.module.scss';

export interface FieldNodeErrorsProps {
  fieldErrors: FieldErrors;
}

const FieldNodeErrors = ({ fieldErrors }: FieldNodeErrorsProps) => {
  const hasOneOfKeywordError = Boolean(fieldErrors.messages.oneOf);

  return (
    <div className={s.fieldNodeErrors}>
      {Object.entries(fieldErrors.messages).map(([keyword, error]) => {
        if (keyword === 'oneOf' || keyword === 'type') {
          return null;
        }

        return <span key={keyword}>{error}</span>;
      })}

      {hasOneOfKeywordError && (
        <>
          OR
          <span>must be unset</span>
        </>
      )}
    </div>
  );
};

export default FieldNodeErrors;
