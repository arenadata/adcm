import { useEffect, useMemo, useState } from 'react';
import type { ConfigurationAttributes, ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { Select } from '@uikit';
import { type JsonSchemaEngineId, jsonSchemaValidationService } from '@utils/jsonSchema/JsonSchemaValidationService';
import { validateWithCfWorkerLibrary } from '@utils/jsonSchema/cfworkerSchemaUtils';
import type { ConfigurationTreeFilter } from '../ConfigurationEditor.types';
import ConfigurationEditor from '../ConfigurationEditor';

export type ValidationCase = {
  description: string;
  schema: ConfigurationSchema;
  datasets: Record<string, ConfigurationData>;
  attributesByDataset?: Record<string, ConfigurationAttributes>;
};

type DatasetId = string;

export type ValidationCaseRunnerProps<CaseId extends string> = {
  caseId: CaseId;
  cases: Record<CaseId, ValidationCase>;
  leftEngine?: JsonSchemaEngineId;
  rightEngine?: JsonSchemaEngineId;
  syncData?: boolean;
};

export const ValidationCaseRunner = <CaseId extends string>({
  caseId,
  cases,
  leftEngine = 'ajv',
  rightEngine = 'cfworker',
  syncData = true,
}: ValidationCaseRunnerProps<CaseId>) => {
  const selected = cases[caseId];
  const datasetIds = useMemo(() => Object.keys(selected.datasets), [selected.datasets]);
  const [datasetId, setDatasetId] = useState<DatasetId>(() => datasetIds[0] as DatasetId);

  useEffect(() => {
    setDatasetId(datasetIds[0] as DatasetId);
  }, [caseId, datasetIds]);

  // While switching caseId, `datasetId` from previous case can linger for one render.
  const effectiveDatasetId = selected.datasets[datasetId] ? datasetId : (datasetIds[0] as DatasetId);
  const safeConfigurationData =
    selected.datasets[effectiveDatasetId] ??
    (jsonSchemaValidationService.generateDefaults('ajv', selected.schema) as ConfigurationData);

  const [configuration, setConfiguration] = useState<ConfigurationData>(safeConfigurationData);
  const [rightConfiguration, setRightConfiguration] = useState<ConfigurationData>(safeConfigurationData);
  const [attributes, setAttributes] = useState<ConfigurationAttributes>({});
  const [areExpandedAll] = useState(false);
  const [filter] = useState<ConfigurationTreeFilter>({
    title: '',
    showAdvanced: false,
    showInvisible: false,
  });

  useEffect(() => {
    setConfiguration(safeConfigurationData);
    setRightConfiguration(safeConfigurationData);
    setAttributes(selected.attributesByDataset?.[effectiveDatasetId] ?? {});
  }, [caseId, effectiveDatasetId, safeConfigurationData, selected.attributesByDataset]);

  useEffect(() => {
    if (rightEngine && syncData) {
      setRightConfiguration(configuration);
    }
  }, [configuration, rightEngine, syncData]);

  const leftErrors = useMemo(
    () => jsonSchemaValidationService.validateRaw(leftEngine, selected.schema, configuration),
    [leftEngine, configuration],
  );
  const rightErrors = useMemo(
    () =>
      rightEngine ? jsonSchemaValidationService.validateRaw(rightEngine, selected.schema, rightConfiguration) : null,
    [rightEngine, rightConfiguration],
  );

  const cfworkerLibraryErrors = useMemo(() => {
    if (rightEngine !== 'cfworker') return null;
    return validateWithCfWorkerLibrary(selected.schema, rightConfiguration);
  }, [rightEngine, rightConfiguration]);

  return (
    <>
      <div style={{ marginBottom: 8 }}>
        <strong>What is checked</strong>
        <div>{selected.description}</div>
      </div>
      Dataset:
      <Select
        options={datasetIds.map((id: string) => ({ value: id, label: id }))}
        value={effectiveDatasetId}
        onChange={(val) => val && setDatasetId(val)}
        dependencyWidth="min-parent"
      />
      <br />
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ marginBottom: 8, fontWeight: 600 }}>Left: {leftEngine}</div>
            <ConfigurationEditor
              schema={selected.schema}
              configuration={configuration}
              attributes={attributes}
              filter={filter}
              areExpandedAll={areExpandedAll}
              onConfigurationChange={setConfiguration}
              onAttributesChange={setAttributes}
              onConfigurationAndAttributesChange={(configurationData, nextAttributes) => {
                setConfiguration(configurationData);
                setAttributes(nextAttributes);
              }}
              validationEngine={leftEngine}
            />
            <div style={{ marginTop: 10 }}>
              <div style={{ marginBottom: 6, fontWeight: 600, fontSize: 12, opacity: 0.9 }}>
                {leftEngine} raw errors
              </div>
              <pre
                style={{
                  margin: 0,
                  maxHeight: 220,
                  overflow: 'auto',
                  padding: 10,
                  borderRadius: 8,
                  border: '1px solid rgba(255,255,255,0.12)',
                  background: 'rgba(0,0,0,0.2)',
                  fontSize: 11,
                  lineHeight: 1.4,
                }}
              >
                {JSON.stringify(leftErrors, null, 2)}
              </pre>
            </div>
          </div>
          {rightEngine && (
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ marginBottom: 8, fontWeight: 600 }}>Right: {rightEngine}</div>
              <ConfigurationEditor
                schema={selected.schema}
                configuration={rightConfiguration}
                attributes={attributes}
                filter={filter}
                areExpandedAll={areExpandedAll}
                onConfigurationChange={setRightConfiguration}
                onAttributesChange={setAttributes}
                onConfigurationAndAttributesChange={(configurationData, nextAttributes) => {
                  setRightConfiguration(configurationData);
                  setAttributes(nextAttributes);
                }}
                validationEngine={rightEngine}
              />
              <div style={{ marginTop: 10 }}>
                <div style={{ marginBottom: 6, fontWeight: 600, fontSize: 12, opacity: 0.9 }}>
                  {rightEngine} raw errors
                </div>
                <pre
                  style={{
                    margin: 0,
                    maxHeight: 220,
                    overflow: 'auto',
                    padding: 10,
                    borderRadius: 8,
                    border: '1px solid rgba(255,255,255,0.12)',
                    background: 'rgba(0,0,0,0.2)',
                    fontSize: 11,
                    lineHeight: 1.4,
                  }}
                >
                  {JSON.stringify(rightErrors, null, 2)}
                </pre>

                {rightEngine === 'cfworker' && (
                  <div style={{ marginTop: 10 }}>
                    <div style={{ marginBottom: 6, fontWeight: 600, fontSize: 12, opacity: 0.9 }}>
                      cfworker library errors (OutputUnit[])
                    </div>
                    <pre
                      style={{
                        margin: 0,
                        maxHeight: 220,
                        overflow: 'auto',
                        padding: 10,
                        borderRadius: 8,
                        border: '1px solid rgba(255,255,255,0.12)',
                        background: 'rgba(0,0,0,0.2)',
                        fontSize: 11,
                        lineHeight: 1.4,
                      }}
                    >
                      {JSON.stringify(cfworkerLibraryErrors, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        <div style={{ width: 520, flex: '0 0 auto' }}>
          <div style={{ marginBottom: 8, fontWeight: 600 }}>Schema</div>
          <pre
            style={{
              margin: 0,
              maxHeight: 'calc(100vh - 260px)',
              overflow: 'auto',
              padding: 12,
              borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.12)',
              background: 'rgba(0,0,0,0.2)',
              fontSize: 12,
              lineHeight: 1.4,
            }}
          >
            {JSON.stringify(selected.schema, null, 2)}
          </pre>
        </div>
      </div>
    </>
  );
};
