import { Card, CardTitle, Switch, Slider } from '../../components/ui';
import { useUiStore, type LayerName } from '../../lib/store';

const LAYER_TOGGLES: { key: LayerName; label: string }[] = [
  { key: 'wtgs', label: 'Wind turbines' },
  { key: 'substations', label: 'Substations' },
  { key: 'towers', label: 'Evacuation towers' },
  { key: 'referenceLines', label: 'Reference lines' },
  { key: 'routes', label: 'Feeder routes' },
  { key: 'parcels', label: 'Parcels' },
  { key: 'restricted', label: 'Restricted zones' }
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
            <span className="text-xs text-text">{item.label}</span>
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
          <span className="text-xs text-text">Interactive route editing</span>
          <Switch
            checked={routeEditMode}
            onCheckedChange={(v) => {
              setRouteEditMode(v);
              if (!v) setLiveBomOverride(null);
            }}
          />
        </div>
        <p className="text-[11px] text-textFaint mt-1.5 mb-0">Drag route vertices on the map; BOM totals update live while enabled.</p>
      </Card>
    </>
  );
}
