import * as RadixSwitch from '@radix-ui/react-switch';

interface SwitchProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}

export function Switch({ checked, onCheckedChange }: SwitchProps) {
  return (
    <RadixSwitch.Root
      checked={checked}
      onCheckedChange={onCheckedChange}
      className="w-[30px] h-[17px] rounded-full bg-borderStrong data-[state=checked]:bg-accent relative flex-none cursor-pointer"
    >
      <RadixSwitch.Thumb className="block w-[13px] h-[13px] rounded-full bg-text translate-x-0.5 data-[state=checked]:translate-x-[15px] data-[state=checked]:bg-accentInk transition-transform" />
    </RadixSwitch.Root>
  );
}
