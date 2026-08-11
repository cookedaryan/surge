package com.power.surge.dto.asset;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Result of persisting an asset import.
 *
 * @param surveyPointsSkipped geotechnical markers (BH, CBR, ERT) recognised but not persisted
 * @param measurementsSkipped Google Earth "Path Measure" artifacts recognised but not persisted
 * @param unclassified        features that could not be classified and were skipped
 * @param duplicatesSkipped   features dropped because the same asset already exists in the project
 * @param countsByType        imported counts keyed by {@link com.power.surge.domain.AssetType} name
 */
public record GeoJsonImportResponse(
        UUID projectId,
        int wtgsImported,
        int substationsImported,
        int towersImported,
        int linesImported,
        int parcelsImported,
        int restrictedAreasImported,
        int surveyPointsSkipped,
        int measurementsSkipped,
        int unclassified,
        int duplicatesSkipped,
        int totalImported,
        Map<String, Integer> countsByType,
        List<WtgResponse> wtgs,
        List<SubstationResponse> substations,
        List<EvacuationTowerResponse> towers,
        List<ReferenceLineResponse> lines
) {
}
