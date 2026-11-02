import type { CSSProperties } from 'react';
import { useCallback } from 'react';
import { Button } from '@uikit';
import { MAPPING_LAYERS_V2_QUERY } from '@utils/mapping/isMappingLayersV2Enabled';

const toolbarStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
  alignItems: 'center',
  marginBottom: 12,
};

type MappingLayersV2ToggleProps = {
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
};

export const MappingLayersV2Toggle = ({ enabled, onEnabledChange }: MappingLayersV2ToggleProps) => {
  const enableV2 = useCallback(() => {
    onEnabledChange(true);
  }, [onEnabledChange]);

  const enableLegacy = useCallback(() => {
    onEnabledChange(false);
  }, [onEnabledChange]);

  return (
    <div style={toolbarStyle}>
      <span>
        Layers: <strong>{enabled ? 'V2' : 'Legacy'}</strong>
        {' | '}
        <code>?{MAPPING_LAYERS_V2_QUERY}=1</code>
      </span>
      <Button variant="secondary" onClick={enableV2}>
        V2
      </Button>
      <Button variant="secondary" onClick={enableLegacy}>
        Legacy
      </Button>
    </div>
  );
};
