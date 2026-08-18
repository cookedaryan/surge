import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ParcelImpactTable } from './ParcelImpactTable';
import type { ParcelImpactSummary } from '../../lib/api';

/**
 * The report returns every parcel imported for the project, not only the ones the route touches.
 * A verification run returned 64 parcels, none of them recorded as affected, under a heading
 * promising impacts.
 */

function parcel(id: string, over: Partial<ParcelImpactSummary> = {}): ParcelImpactSummary {
  return {
    parcelId: id,
    ownerName: `Owner ${id}`,
    acquisitionCostPerM2: 55,
    affectedAreaM2: 0,
    estimatedCompensationCost: 0,
    selectedPresentValue: null,
    ...over
  };
}

describe('ParcelImpactTable', () => {
  it('says nothing was intersected rather than listing the whole cadastre', () => {
    render(<ParcelImpactTable parcels={Array.from({ length: 64 }, (_, i) => parcel(`PCL-${i}`))} />);

    expect(screen.getByText(/no parcel intersection was recorded/i)).toBeTruthy();
    expect(screen.getByText(/64 parcels considered/i)).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('lists only the parcels the route actually touches', () => {
    render(
      <ParcelImpactTable
        parcels={[
          parcel('PCL-001', { affectedAreaM2: 320 }),
          parcel('PCL-002'),
          parcel('PCL-003', { selectedPresentValue: 12_500 })
        ]}
      />
    );

    expect(screen.getByText('PCL-001')).toBeTruthy();
    expect(screen.getByText('PCL-003')).toBeTruthy();
    expect(screen.queryByText('PCL-002')).toBeNull();
    expect(screen.getByText('2 of 3 parcels affected')).toBeTruthy();
  });

  it('counts a priced acquisition as an impact even with no recorded area', () => {
    render(<ParcelImpactTable parcels={[parcel('PCL-009', { selectedPresentValue: 900 })]} />);

    expect(screen.getByText('PCL-009')).toBeTruthy();
  });

  it('caps a long list until asked for the rest', async () => {
    const many = Array.from({ length: 30 }, (_, i) => parcel(`PCL-${String(i).padStart(3, '0')}`, { affectedAreaM2: 100 + i }));
    render(<ParcelImpactTable parcels={many} />);

    expect(screen.queryByText('PCL-020')).toBeNull();

    await userEvent.click(screen.getByRole('button', { name: /show all 30/i }));

    expect(screen.getByText('PCL-020')).toBeTruthy();
    expect(screen.getByRole('button', { name: /show fewer/i })).toBeTruthy();
  });

  it('offers no expander when everything already fits', () => {
    render(<ParcelImpactTable parcels={[parcel('PCL-001', { affectedAreaM2: 50 })]} />);

    expect(screen.queryByRole('button')).toBeNull();
  });
});
