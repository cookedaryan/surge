package com.power.surge.dto.asset;

import com.power.surge.domain.AssetType;
import com.power.surge.domain.LineType;
import com.power.surge.domain.WtgStatus;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Dry-run classification of an uploaded file. Nothing is persisted until the corresponding
 * {@code /commit} call, so a mis-detected file costs the user a glance rather than a cleanup.
 *
 * @param importId          handle used to commit this import
 * @param countsByType      how many features resolved to each {@link AssetType}
 * @param features          per-feature classification, including the rule that fired
 * @param duplicatesRemoved placemarks dropped as exact duplicates during conversion
 * @param skippedByGeometry geometries present in the source that could not be read at all
 */
public record AssetImportPreviewResponse(
        UUID projectId,
        String importId,
        String fileName,
        int totalPlacemarks,
        int duplicatesRemoved,
        Map<String, Integer> countsByType,
        Map<String, Integer> skippedByGeometry,
        List<ClassifiedFeature> features
) {

    /**
     * @param geometryType Point, LineString or Polygon — drives which controls the UI offers
     * @param lineType     for LineStrings only; null otherwise
     * @param matchedRule  which rule in the classification chain fired
     * @param evidence     the folder segment or name that caused the match
     * @param vertexCount  useful for telling a 1122-vertex river outline from a 5-vertex stray
     */
    public record ClassifiedFeature(
            int index,
            String geometryType,
            String externalId,
            String kmlFolder,
            AssetType classifiedAs,
            LineType lineType,
            WtgStatus status,
            String matchedRule,
            String evidence,
            int vertexCount,
            double longitude,
            double latitude
    ) {
    }
}
