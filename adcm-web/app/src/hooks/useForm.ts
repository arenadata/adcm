import { useMemo, useState } from 'react';

export type FormErrors<FormData> = Partial<Record<keyof FormData, string | undefined>>;

export const useForm = <FormData, ErrorsData extends object = FormErrors<FormData>>(
  initialFormData: FormData,
  initialErrorsData: ErrorsData = {} as ErrorsData,
) => {
  const [formData, setFormData] = useState<FormData>(initialFormData);

  const [errors, setErrors] = useState<ErrorsData>(initialErrorsData);

  const isValid = useMemo<boolean>(() => {
    return !Object.values(errors).some((v) => !!v);
  }, [errors]);

  const handleChangeFormData = (changes: Partial<FormData>) => {
    setFormData({
      ...formData,
      ...changes,
    });
  };

  return {
    isValid,
    formData,
    setFormData,
    errors,
    setErrors,
    handleChangeFormData,
  };
};
