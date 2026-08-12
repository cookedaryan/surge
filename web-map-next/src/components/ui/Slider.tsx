import * as RadixSlider from '@radix-ui/react-slider';

interface SliderProps {
  value: number;
  onValueChange: (value: number) => void;
  min: number;
  max: number;
  step: number;
}

export function Slider({ value, onValueChange, min, max, step }: SliderProps) {
  return (
    <RadixSlider.Root
      className="relative flex items-center w-full h-4"
      value={[value]}
      onValueChange={([v]) => onValueChange(v)}
      min={min}
      max={max}
      step={step}
    >
      <RadixSlider.Track className="relative h-1 flex-1 rounded-full bg-borderStrong">
        <RadixSlider.Range className="absolute h-full rounded-full bg-accent" />
      </RadixSlider.Track>
      <RadixSlider.Thumb className="block w-3.5 h-3.5 rounded-full bg-accent border-2 border-panel shadow-[0_0_0_1px_var(--accent)] cursor-pointer" />
    </RadixSlider.Root>
  );
}
