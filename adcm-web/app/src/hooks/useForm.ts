import { useMemo, useState } from 'react';

export const useForm = <FormData, ErrorsData extends object = Partial<Record<keyof FormData, string | undefined>>>(
  initialFormData: FormData,
  initialErrorsData: ErrorsData = {} as ErrorsData,
) => {
  const [formData, setFormData] = useState<FormData>(initialFormData);

  const [errors, setErrors] = useState<ErrorsData>(initialErrorsData);

  const isValid = useMemo<boolean>(() => {
    return !Object.values(errors).some((v) => !!v);
  }, [errors]);

  return {
    isValid,
    formData,
    setFormData,
    errors,
    setErrors,
  };
};
