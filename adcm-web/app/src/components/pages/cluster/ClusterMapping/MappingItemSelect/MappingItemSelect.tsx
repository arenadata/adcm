import { Popover, PopoverPanelDefault, MultiSelectPanel, SelectOption } from '@uikit';

export interface MappingItemSelectProps<T> {
  isOpen: boolean;
  triggerRef: React.RefObject<HTMLElement>;
  options: SelectOption<T>[];
  value: T[];
  checkAllLabel: string;
  searchPlaceholder: string;
  onOpenChange: (isOpen: boolean) => void;
  onChange: (value: T[]) => void;
}

const MappingItemSelect = <T,>({
  isOpen,
  triggerRef,
  options,
  value,
  checkAllLabel,
  searchPlaceholder,
  onChange,
  onOpenChange,
}: MappingItemSelectProps<T>) => {
  return (
    <Popover
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      triggerRef={triggerRef}
      dependencyWidth="min-parent"
      offset={12}
    >
      <PopoverPanelDefault data-test="add-mapping-popover">
        <MultiSelectPanel
          options={options}
          value={value}
          onChange={onChange}
          checkAllLabel={checkAllLabel}
          maxHeight={400}
          isSearchable={true}
          searchPlaceholder={searchPlaceholder}
        />
      </PopoverPanelDefault>
    </Popover>
  );
};

export default MappingItemSelect;
