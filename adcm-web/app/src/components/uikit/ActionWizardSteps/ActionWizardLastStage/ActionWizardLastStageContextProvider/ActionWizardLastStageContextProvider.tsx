import { useForm } from '@hooks';
import {
  ActionWizardLastStageContext,
  type AdcmWizardLastStageContextProps,
} from './ActionWizardLastStageContext.context';

interface LastStageContextProviderProps {
  children: React.ReactNode;
}

const initialFormData: AdcmWizardLastStageContextProps = {
  isVerbose: false,
  shouldBlockObject: true,
  description:'',
};

const ActionWizardLastStageContextProvider: React.FC<LastStageContextProviderProps> = ({ children }) => {
  const { formData, handleChangeFormData } = useForm(initialFormData);

  const contextValue = {
    formData,
    onChange: handleChangeFormData,
  };

  return <ActionWizardLastStageContext.Provider value={contextValue}>{children}</ActionWizardLastStageContext.Provider>;
};

export default ActionWizardLastStageContextProvider;
