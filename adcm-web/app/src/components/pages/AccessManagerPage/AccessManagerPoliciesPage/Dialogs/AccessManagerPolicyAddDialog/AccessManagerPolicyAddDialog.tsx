import React from 'react';
import { Dialog, FormField, FormFieldsContainer, Input, Select, TabsBlock } from '@uikit';
import MultiSelect from '@uikit/Select/MultiSelect/MultiSelect';
import { useAccessManagerPolicyAddDialog } from './useAccessManagerPolicyAddDialog';
import s from './AccessManagerPolicyAddDialog.module.scss';
import TabButton from '@uikit/Tabs/TabButton';
import AccessManagerPolicyAddDialogStepTwo from './AccessManagerPolicyAddDialogStepTwo/AccessManagerPolicyAddDialogStepTwo';
import { useDispatch } from 'hooks';
import { getObjectCandidates } from '@store/adcm/policies/policiesSlice';
import { Steps } from './AccessManagerPolicyAddDialog.constants';
import { ChangeFormDataPayload } from '@pages/AccessManagerPage/AccessManagerPoliciesPage/Dialogs/AccessManagerPolicyAddDialog/AccessManagerPolicyAddDialog.types';
import { isValidSecondStep } from '@pages/AccessManagerPage/AccessManagerPoliciesPage/Dialogs/AccessManagerPolicyAddDialog/AccessManagerPolicyAddDialog.utils';

const AccessManagerPolicyAddDialog: React.FC = () => {
  const dispatch = useDispatch();
  const {
    isOpen,
    isEdit,
    formData,
    isValidFirstStep,
    currentStep,
    setCurrentStep,
    submit,
    onClose,
    onChangeFormData,
    relatedData: { groupsOptions, rolesOptions, roles, steps },
  } = useAccessManagerPolicyAddDialog();

  const isCurrentStepMainInfo = currentStep === Steps.MainInfo;
  const isCurrentStepObject = currentStep === Steps.Object;

  const handlePolicyNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ policyName: event.target.value });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ description: event.target.value });
  };

  const handleRoleChange = (roleId: number | null) => {
    onChangeFormData({
      roleId: roleId,
      objectTypes: roles.find((role) => role.id === roleId)?.parametrizedByType,
      clusterIds: [],
      serviceClusterIds: [],
      serviceName: '',
      hostIds: [],
      hostproviderIds: [],
    });
    if (roleId) {
      dispatch(getObjectCandidates(roleId));
    }
  };

  const handleGroupsChange = (groupIds: number[]) => {
    onChangeFormData({ groupIds: groupIds });
  };

  const changeSecondStepData = (value: ChangeFormDataPayload) => {
    onChangeFormData(value);
  };

  const handleChangeStep = (event: React.MouseEvent<HTMLButtonElement>) => {
    const stepKey = event.currentTarget.dataset.stepKey ?? '';
    setCurrentStep(stepKey);
  };

  const handleSwitchStep = () => {
    setCurrentStep(Steps.Object);
  };

  return (
    <>
      <Dialog
        isOpen={isOpen}
        onOpenChange={onClose}
        title={`${isEdit ? 'Edit' : 'Create new'} policy`}
        actionButtonLabel={isCurrentStepMainInfo ? 'Next' : isEdit ? 'Update' : 'Create'}
        isActionDisabled={isCurrentStepMainInfo ? !isValidFirstStep : !isValidSecondStep(formData)}
        onAction={isCurrentStepMainInfo ? handleSwitchStep : submit}
        onCancel={onClose}
      >
        <div className={s.policyAddDialog__stepsPanel}>
          <TabsBlock variant="secondary">
            <TabButton
              className={isValidFirstStep ? s.policyAddDialog__stepsPanel__stepButton_valid : ''}
              isActive={isCurrentStepMainInfo}
              data-step-key={Steps.MainInfo}
              onClick={handleChangeStep}
            >
              <span className={s.policyAddDialog__stepNumber}>1</span>
              {steps[0].title}
            </TabButton>
            <TabButton
              className={isValidSecondStep(formData) ? s.policyAddDialog__stepsPanel__stepButton_valid : ''}
              disabled={!isValidFirstStep}
              isActive={isCurrentStepObject}
              data-step-key={Steps.Object}
              onClick={handleChangeStep}
            >
              <span className={s.policyAddDialog__stepNumber}>2</span>
              {steps[1].title}
            </TabButton>
          </TabsBlock>
        </div>
        {isCurrentStepMainInfo && (
          <FormFieldsContainer>
            <FormField label="Policy name">
              <Input
                value={formData.policyName}
                type="text"
                onChange={handlePolicyNameChange}
                placeholder="Enter unique name"
                autoFocus
              />
            </FormField>

            <FormField label="Description">
              <Input
                value={formData.description}
                type="text"
                onChange={handleDescriptionChange}
                placeholder="Enter description"
              />
            </FormField>

            <FormField label="Role">
              <Select
                placeholder="Select role"
                value={formData.roleId}
                onChange={handleRoleChange}
                options={rolesOptions}
                maxHeight={400}
              />
            </FormField>

            <FormField label="Groups">
              <MultiSelect
                placeholder="Select groups"
                checkAllLabel="All groups"
                value={formData.groupIds}
                onChange={handleGroupsChange}
                options={groupsOptions}
                maxHeight={310}
              />
            </FormField>
          </FormFieldsContainer>
        )}
        {isCurrentStepObject && (
          <AccessManagerPolicyAddDialogStepTwo formData={formData} changeFormData={changeSecondStepData} />
        )}
      </Dialog>
    </>
  );
};
export default AccessManagerPolicyAddDialog;
