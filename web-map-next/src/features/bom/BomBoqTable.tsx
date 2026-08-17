import React from 'react';
import { Card, CardTitle } from '../../components/ui';
import type { BomReport } from '../../lib/api/types';

interface BomBoqTableProps {
  bom: BomReport | null | undefined;
}

export function BomBoqTable({ bom }: BomBoqTableProps) {
  if (!bom) return null;

  const conductorTotals = React.useMemo(() => {
    if (!bom.segmentDetails) return [];
    const grouped = bom.segmentDetails.reduce((acc, seg) => {
      let type = seg.cableTypeId || 'Unknown';
      if (seg.cableTypeId && seg.cableParallelCount > 1) {
        if (seg.cableParallelCount === 2) {
          type = `Twin ${seg.cableTypeId} (2×)`;
        } else {
          type = `${seg.cableTypeId} (${seg.cableParallelCount}×)`;
        }
      }
      acc[type] = (acc[type] || 0) + seg.lengthMeters;
      return acc;
    }, {} as Record<string, number>);
    return Object.entries(grouped)
      .map(([type, lengthMeters]) => ({ type, lengthKm: lengthMeters / 1000 }))
      .sort((a, b) => b.lengthKm - a.lengthKm);
  }, [bom.segmentDetails]);

  const poleTypes = React.useMemo(() => {
    if (!bom.poleCountByType) return [];
    return Object.entries(bom.poleCountByType)
      .map(([type, count]) => ({ type, count }))
      .sort((a, b) => b.count - a.count);
  }, [bom.poleCountByType]);

  const poleRoles = React.useMemo(() => {
    if (!bom.poleCountByRole) return [];
    return Object.entries(bom.poleCountByRole)
      .map(([role, count]) => ({ role, count }))
      .sort((a, b) => b.count - a.count);
  }, [bom.poleCountByRole]);

  return (
    <Card className="mt-3">
      <CardTitle>Bill of Quantities</CardTitle>

      <div className="space-y-4 text-sm mt-3">
        {/* Conductor Schedule */}
        <div>
          <h3 className="text-xs font-semibold uppercase text-textFaint mb-2">Conductor Schedule</h3>
          {conductorTotals.length > 0 ? (
            <div className="border border-border rounded-md overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-surface2 border-b border-border">
                  <tr>
                    <th className="px-2 py-1.5 font-medium text-textFaint">Cable Type</th>
                    <th className="px-2 py-1.5 font-medium text-textFaint text-right">Length (km)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {conductorTotals.map((item) => (
                    <tr key={item.type} className="bg-panel">
                      <td className="px-2 py-1.5">{item.type}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular">{item.lengthKm.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-textFaint text-xs">No conductor data available.</div>
          )}
        </div>

        {/* Pole Schedule by Type */}
        <div>
          <h3 className="text-xs font-semibold uppercase text-textFaint mb-2">Poles by Type</h3>
          {poleTypes.length > 0 ? (
            <div className="border border-border rounded-md overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-surface2 border-b border-border">
                  <tr>
                    <th className="px-2 py-1.5 font-medium text-textFaint">Pole Type</th>
                    <th className="px-2 py-1.5 font-medium text-textFaint text-right">Count</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {poleTypes.map((item) => (
                    <tr key={item.type} className="bg-panel">
                      <td className="px-2 py-1.5">{item.type}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular">{item.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-textFaint text-xs">No pole data available.</div>
          )}
        </div>

        {/* Pole Schedule by Role */}
        <div>
          <h3 className="text-xs font-semibold uppercase text-textFaint mb-2">Poles by Role</h3>
          {poleRoles.length > 0 ? (
            <div className="border border-border rounded-md overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-surface2 border-b border-border">
                  <tr>
                    <th className="px-2 py-1.5 font-medium text-textFaint">Role</th>
                    <th className="px-2 py-1.5 font-medium text-textFaint text-right">Count</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {poleRoles.map((item) => (
                    <tr key={item.role} className="bg-panel">
                      <td className="px-2 py-1.5">{item.role}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular">{item.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-textFaint text-xs">No pole role data available.</div>
          )}
        </div>

        {/* Land & Right of Way */}
        {(bom.totalAffectedAreaM2 > 0 || bom.rowWidthMeters > 0) && (
          <div>
            <h3 className="text-xs font-semibold uppercase text-textFaint mb-2">Land & Right of Way</h3>
            <div className="border border-border rounded-md overflow-hidden bg-panel mb-4">
              <div className="flex justify-between px-2 py-1.5 border-b border-border">
                <span className="text-textFaint">RoW Width</span>
                <span className="font-mono tabular">{bom.rowWidthMeters} m</span>
              </div>
              <div className="flex justify-between px-2 py-1.5 border-b border-border">
                <span className="text-textFaint">Total Affected Area</span>
                <span className="font-mono tabular">{(bom.totalAffectedAreaM2 / 10000).toFixed(2)} ha</span>
              </div>
            </div>

            {bom.parcelImpactSummaries && bom.parcelImpactSummaries.length > 0 && (
              <div className="border border-border rounded-md overflow-x-auto">
                <table className="w-full text-left whitespace-nowrap">
                  <thead className="bg-surface2 border-b border-border">
                    <tr>
                      <th className="px-2 py-1.5 font-medium text-textFaint">Parcel ID</th>
                      <th className="px-2 py-1.5 font-medium text-textFaint">Owner</th>
                      <th className="px-2 py-1.5 font-medium text-textFaint">Instrument</th>
                      <th className="px-2 py-1.5 font-medium text-textFaint text-right">Present Value</th>
                      <th className="px-2 py-1.5 font-medium text-textFaint">Price Basis</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {bom.parcelImpactSummaries.map((parcel, idx) => (
                      <tr key={idx} className="bg-panel">
                        <td className="px-2 py-1.5">{parcel.parcelId}</td>
                        <td className="px-2 py-1.5">{parcel.ownerName || 'Unknown'}</td>
                        <td className="px-2 py-1.5">{parcel.transactionMode || '-'}</td>
                        <td className="px-2 py-1.5 text-right font-mono tabular">
                          {parcel.selectedPresentValue != null
                            ? parcel.selectedPresentValue.toLocaleString(undefined, {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                              })
                            : '-'}
                        </td>
                        <td className="px-2 py-1.5">{parcel.priceBasis || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
