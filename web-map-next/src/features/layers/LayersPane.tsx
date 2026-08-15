import { Card, CardTitle, Switch, Slider } from '../../components/ui';
import { useUiStore, type LayerName } from '../../lib/store';

const LAYER_TOGGLES: { key: LayerName; label: string }[] = [
  { key: 'wtgs', label: 'Wind turbines' },
  { key: 'substations', label: 'Substations' },
  { key: 'towers', label: 'Evacuation towers' },
  { key: 'routes', label: 'Feeder routes' }
];

// Roads/HT-lines and parcels are soft, crossable-with-penalty constraints; restricted zones
// are hard exclusions the router must never enter. Kept as separate toggles/styles per
// docs/whats-next.md §7.4 rather than one generic "constraints" layer.
const CONSTRAINT_TOGGLES: { key: LayerName; label: string; hint: string }[] = [
  { key: 'referenceLines', label: 'Roads / HT-lines', hint: 'Soft — crossable with penalty' },
  { key: 'parcels', label: 'Parcels', hint: 'Soft — crossable with penalty' },
  { key: 'restricted', label: 'Restricted zones', hint: 'Hard exclusion' }
];

const POLE_TOGGLES: { key: LayerName; label: string }[] = [
  { key: 'polesTerminal', label: 'Terminal / dead-end' },
  { key: 'polesAngle', label: 'Angle / tension' },
  { key: 'polesIntermediate', label: 'Tangent / suspension' },
  { key: 'polesJunction', label: 'Junction' }
];

export function LayersPane() {
  const layerVisibility = useUiStore((s) => s.layerVisibility);
  const toggleLayer = useUiStore((s) => s.toggleLayer);
  const parcelOpacity = useUiStore((s) => s.parcelOpacity);
  const setParcelOpacity = useUiStore((s) => s.setParcelOpacity);
  const restrictedOpacity = useUiStore((s) => s.restrictedOpacity);
  const setRestrictedOpacity = useUiStore((s) => s.setRestrictedOpacity);
  const routeEditMode = useUiStore((s) => s.routeEditMode);
  const setRouteEditMode = useUiStore((s) => s.setRouteEditMode);
  const setLiveBomOverride = useUiStore((s) => s.setLiveBomOverride);

  return (
    <>
      <Card>
        <CardTitle>Map Layer Controls</CardTitle>
        {LAYER_TOGGLES.map((item) => (
          <div key={item.key} className="flex items-center justify-between py-1.5 border-b border-border last:border-b-0">
            <span className="text-[11.5px] text-text">{item.label}</span>
            <Switch checked={layerVisibility[item.key]} onCheckedChange={() => toggleLayer(item.key)} />
          </div>
        ))}
      </Card>
      <Card>
        <CardTitle>Constraints</CardTitle>
        {CONSTRAINT_TOGGLES.map((item) => (
          <div key={item.key} className="flex items-center justify-between py-1.5 border-b border-border last:border-b-0">
            <div>
              <span className="text-[11.5px] text-text block">{item.label}</span>
              <span className="text-[11.5px] text-textFaint">{item.hint}</span>
            </div>
            <Switch checked={layerVisibility[item.key]} onCheckedChange={() => toggleLayer(item.key)} />
          </div>
        ))}
      </Card>
      <Card>
        <CardTitle>Pole Classes</CardTitle>
        {POLE_TOGGLES.map((item) => (
          <div key={item.key} className="flex items-center justify-between py-1.5 border-b border-border last:border-b-0">
            <span className="text-[11.5px] text-text">{item.label}</span>
            <Switch checked={layerVisibility[item.key]} onCheckedChange={() => toggleLayer(item.key)} />
          </div>
        ))}
      </Card>
      <Card>
        <CardTitle>Polygon Opacity</CardTitle>
        <div className="flex flex-col gap-3">
          <div>
            <label className="flex justify-between text-[11.5px] text-textMuted mb-1.5">
              Parcels <span className="font-mono text-text tabular">{parcelOpacity.toFixed(2)}</span>
            </label>
            <Slider value={parcelOpacity} onValueChange={setParcelOpacity} min={0} max={1} step={0.05} />
          </div>
          <div>
            <label className="flex justify-between text-[11.5px] text-textMuted mb-1.5">
              Restricted areas <span className="font-mono text-text tabular">{restrictedOpacity.toFixed(2)}</span>
            </label>
            <Slider value={restrictedOpacity} onValueChange={setRestrictedOpacity} min={0} max={1} step={0.05} />
          </div>
        </div>
      </Card>
      <Card>
        <div className="flex items-center justify-between">
          <span className="text-[11.5px] text-text">Interactive route editing</span>
          <Switch
            checked={routeEditMode}
            onCheckedChange={(v) => {
              setRouteEditMode(v);
              if (!v) setLiveBomOverride(null);
            }}
          />
        </div>
        <p className="text-[11.5px] text-textFaint mt-1.5 mb-0">Drag route vertices on the map; BOM totals update live while enabled.</p>
      </Card>
    </>
  );
}
