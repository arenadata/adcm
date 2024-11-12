import React from 'react';
import Tag from '@uikit/Tags/Tag';
import IconButton from '@uikit/IconButton/IconButton';
import Tags from '@uikit/Tags/Tags';
import type { MultiPropsParams } from '@uikit/Select/Select.types';
import s from './MultiSelectResults.module.scss';

type MultiSelectResultsProps<T> = MultiPropsParams<T>;

const MultiSelectResults = <T,>({
  value: selectedValues,
  options: originalOptions,
  onChange,
}: MultiSelectResultsProps<T>) => {
  const getHandleChange = (value: T) => () => {
    const newValues = [...selectedValues];
    newValues.splice(newValues.indexOf(value), 1);
    onChange?.([...newValues]);
  };

  return (
    <Tags className={s.multiSelectResults}>
      {selectedValues.map((value) => {
        const label = originalOptions.find(({ value: val }) => value === val)?.label;
        return (
          <Tag
            key={value?.toString()}
            className={s.multiSelectResults__tag}
            endAdornment={
              <IconButton
                icon="g1-remove"
                variant="secondary"
                size={20}
                onClick={getHandleChange(value)}
                title="Remove"
              />
            }
          >
            <div className={s.multiSelectResults__tagContent}>{label}</div>
          </Tag>
        );
      })}
    </Tags>
  );
};

export default MultiSelectResults;
