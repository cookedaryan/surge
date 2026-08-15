import { useState } from 'react';
import { Dialog, Button, Select } from '../../components/ui';
import { ASSET_TYPES, ASSET_TYPE_LABELS, LINE_TYPES, LINE_TYPE_LABELS } from '../../lib/classify';
import { useCommitImport } from '../../lib/query';
import { useUiStore } from '../../lib/store';
import type { ImportPreview } from '../../lib/api';

interface ImportPreviewModalProps {
  preview: ImportPreview | null;
  onClose: () => void;
}

const GEOMETRY_GLYPH: Record<string, string> = { Point: '●', LineString: '╱', Polygon: '▭' };

export function ImportPreviewModal({ preview, onClose }: ImportPreviewModalProps) {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const showToast = useUiStore((s) => s.showToast);
  const commitImport = useCommitImport(currentProjectId);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [bulkType, setBulkType] = useState('');
  const [defaultCapacity, setDefaultCapacity] = useState('');

  if (!preview) return null;

  const counts = preview.countsByType || {};
  const unknownCount = counts.UNKNOWN || 0;
  const skipped = preview.skippedByGeometry || {};
  const skippedTotal = Object.values(skipped).reduce((sum, n) => sum + n, 0);

  const notes: string[] = [];
  if ((preview.duplicatesRemoved || 0) > 0) {
    notes.push(`${preview.duplicatesRemoved} duplicate placemark(s) removed — this file repeats its own folder tree.`);
  }
  if (skippedTotal > 0) {
    const detail = Object.entries(skipped).map(([type, n]) => `${n} ${type}`).join(', ');
    notes.push(`${skippedTotal} non-point feature(s) not imported as assets (${detail}).`);
  }
  if (unknownCount > 0) {
    notes.push(`${unknownCount} feature(s) could not be classified and will be skipped unless you assign a type.`);
  }

  function setOverride(externalId: string, type: string) {
    setOverrides((prev) => ({ ...prev, [externalId]: type }));
  }

  function applyBulk() {
    if (!bulkType || !preview) return;
    const next: Record<string, string> = {};
    for (const feature of preview.features) next[feature.externalId] = bulkType;
    setOverrides(next);
  }

  async function handleCommit() {
    if (!preview) return;
    try {
      const result = await commitImport.mutateAsync({
        importId: preview.importId,
        overrides,
        defaultCapacityMw: defaultCapacity ? parseFloat(defaultCapacity) : null,
        skipUnclassified: true
      });
      const parts: string[] = [];
      if (result.wtgsImported) parts.push(`${result.wtgsImported} turbines`);
      if (result.substationsImported) parts.push(`${result.substationsImported} substations`);
      if (result.towersImported) parts.push(`${result.towersImported} towers`);
      if (result.unclassified) parts.push(`${result.unclassified} skipped`);
      showToast(`Imported ${parts.join(', ') || 'nothing'}`, 'success');
      setOverrides({});
      onClose();
    } catch (err) {
      showToast(`Import failed: ${(err as Error).message || err}`, 'error');
    }
  }

  return (
    <Dialog
      open={!!preview}
      onOpenChange={(open) => { if (!open) onClose(); }}
      title={`Import Preview — ${preview.fileName || 'Uploaded file'}`}
      widthClassName="w-[680px]"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={commitImport.isPending} onClick={handleCommit}>
            {commitImport.isPending ? 'Importing…' : 'Confirm Import'}
          </Button>
        </>
      }
    >
      <div className="flex flex-wrap gap-1.5 mb-2.5">
        {Object.entries(counts)
          .filter(([, count]) => count > 0)
          .map(([type, count]) => (
            <div key={type} className="text-[11.5px] font-semibold px-2 py-1 rounded-full bg-surface2 border border-border text-textMuted">
              <strong className="text-text">{count}</strong> {ASSET_TYPE_LABELS[type as keyof typeof ASSET_TYPE_LABELS] || type}
            </div>
          ))}
      </div>
      {notes.length > 0 && (
        <div className="flex flex-col gap-1 mb-2.5">
          {notes.map((note, i) => (
            <div key={i} className="text-[11.5px] text-warning">{note}</div>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 mb-2.5">
        <Select
          value={bulkType}
          onValueChange={setBulkType}
          options={Object.keys(ASSET_TYPES).map((t) => ({ value: t, label: ASSET_TYPE_LABELS[t as keyof typeof ASSET_TYPE_LABELS] }))}
          className="min-w-[160px]"
        />
        <Button size="sm" onClick={applyBulk}>Apply to all rows</Button>
        <input
          className="h-[26px] w-[120px] rounded-md border border-borderStrong bg-surface2 px-2 text-[11.5px] text-text outline-none focus:border-accent"
          placeholder="Default MW"
          value={defaultCapacity}
          onChange={(e) => setDefaultCapacity(e.target.value)}
        />
      </div>
      <div className="overflow-x-auto border border-border rounded-md">
        <table className="w-full text-[11.5px] border-collapse">
          <thead>
            <tr className="bg-surface2 text-textFaint uppercase tracking-wide text-[11.5px]">
              <th className="text-left px-2 py-1.5">Geom</th>
              <th className="text-left px-2 py-1.5">Name</th>
              <th className="text-left px-2 py-1.5">Folder</th>
              <th className="text-left px-2 py-1.5">Type</th>
              <th className="text-left px-2 py-1.5">Status</th>
              <th className="text-left px-2 py-1.5">Rule</th>
            </tr>
          </thead>
          <tbody>
            {preview.features.map((feature) => {
              const isLine = feature.geometryType === 'LineString';
              const currentValue = overrides[feature.externalId] ?? (isLine ? feature.lineType : feature.classifiedAs) ?? 'UNKNOWN';
              const options = isLine
                ? Object.keys(LINE_TYPES).map((t) => ({ value: t, label: LINE_TYPE_LABELS[t as keyof typeof LINE_TYPE_LABELS] }))
                : Object.keys(ASSET_TYPES).map((t) => ({ value: t, label: ASSET_TYPE_LABELS[t as keyof typeof ASSET_TYPE_LABELS] }));
              const unresolved = feature.classifiedAs === 'UNKNOWN' || (isLine && feature.lineType === 'UNKNOWN');
              return (
                <tr key={feature.externalId} className={unresolved ? 'bg-dangerSoft' : ''}>
                  <td className="px-2 py-1 text-textFaint" title={feature.geometryType}>{GEOMETRY_GLYPH[feature.geometryType] || '?'}</td>
                  <td className="px-2 py-1 text-text">{feature.externalId || <em>unnamed</em>}</td>
                  <td className="px-2 py-1 text-textFaint">{feature.kmlFolder || '—'}</td>
                  <td className="px-2 py-1">
                    <Select value={currentValue} onValueChange={(v) => setOverride(feature.externalId, v)} options={options} className="h-6 text-[11.5px]" />
                  </td>
                  <td className="px-2 py-1 text-textFaint">{feature.status && feature.status !== 'UNKNOWN' ? feature.status.replace(/_/g, ' ') : '—'}</td>
                  <td className="px-2 py-1 text-textFaint" title={feature.evidence || ''}>{feature.matchedRule.replace(/_/g, ' ').toLowerCase()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Dialog>
  );
}
