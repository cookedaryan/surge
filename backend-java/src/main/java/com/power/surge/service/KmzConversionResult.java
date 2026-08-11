package com.power.surge.service;

import java.util.Map;

/**
 * Outcome of converting a KMZ/KML archive into a GeoJSON FeatureCollection.
 *
 * @param featureCollection    RFC 7946 FeatureCollection of Point, LineString and Polygon features
 * @param totalPlacemarks      every Placemark encountered, whatever its geometry
 * @param pointPlacemarks      Point placemarks encountered, before deduplication
 * @param linePlacemarks       LineString placemarks encountered, before deduplication
 * @param polygonPlacemarks    Polygon placemarks encountered, before deduplication
 * @param duplicatesRemoved    placemarks dropped as exact duplicates of an earlier feature
 * @param skippedByGeometry    counts of geometries that could not be imported, by type
 */
public record KmzConversionResult(
        Map<String, Object> featureCollection,
        int totalPlacemarks,
        int pointPlacemarks,
        int linePlacemarks,
        int polygonPlacemarks,
        int duplicatesRemoved,
        Map<String, Integer> skippedByGeometry
) {

    public int importedFeatures() {
        return pointPlacemarks + linePlacemarks + polygonPlacemarks - duplicatesRemoved;
    }
}
