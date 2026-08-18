import * as RadixSelect from '@radix-ui/react-select';

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  value: string;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  className?: string;
}

export function Select({ value, onValueChange, options, className }: SelectProps) {
  return (
    <RadixSelect.Root value={value} onValueChange={onValueChange}>
      <RadixSelect.Trigger
        className={`h-8 rounded-md border border-borderStrong bg-surface2 px-2 text-sm text-text flex items-center justify-between gap-2
                    transition-colors duration-fast ease-out hover:border-textFaint data-[state=open]:border-accent ${className || ''}`}
      >
        <RadixSelect.Value />
        <RadixSelect.Icon className="text-textFaint transition-transform duration-fast ease-out [[data-state=open]_&]:rotate-180">
          ▾
        </RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content className="bg-panel border border-borderStrong rounded-md overflow-hidden z-[10010] shadow-3
                     data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out">
          <RadixSelect.Viewport>
            {options.map((opt) => (
              <RadixSelect.Item
                key={opt.value}
                value={opt.value}
                className="px-2.5 py-1.5 text-sm text-text cursor-pointer outline-none transition-colors duration-fast
                           data-[highlighted]:bg-accentSoft data-[highlighted]:text-accent"
              >
                <RadixSelect.ItemText>{opt.label}</RadixSelect.ItemText>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  );
}
