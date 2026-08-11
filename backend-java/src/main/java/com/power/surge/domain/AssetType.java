package com.power.surge.domain;

/**
 * Classification of a point asset ingested from a KMZ/KML or GeoJSON source.
 *
 * <p>{@link #UNKNOWN} is deliberate: an unrecognised placemark must never be silently
 * defaulted to {@link #WTG}, which is the defect this enum was introduced to fix.</p>
 */
public enum AssetType {

    /** Wind turbine generator location. */
    WTG,

    /** Pooling substation / grid substation / switching yard. */
    SUBSTATION,

    /** Transmission or evacuation line tower, angle point or gantry. */
    EVACUATION_TOWER,

    /** Geotechnical or survey marker (borehole, CBR, ERT, plate load test). Stored for reference only. */
    SURVEY_POINT,

    /** Polygon: a cadastral land parcel carrying an acquisition cost. */
    PARCEL,

    /** Polygon: an exclusion zone — water body, forest, sanctuary, settlement setback. */
    RESTRICTED_AREA,

    /** LineString: an existing road, transmission line, watercourse or route. See {@link LineType}. */
    REFERENCE_LINE,

    /** Could not be classified. Requires an explicit user decision before persistence. */
    UNKNOWN;

    public boolean isPoint() {
        return this == WTG || this == SUBSTATION || this == EVACUATION_TOWER || this == SURVEY_POINT;
    }

    public static AssetType fromNullable(String value) {
        if (value == null || value.isBlank()) {
            return UNKNOWN;
        }
        String normalized = value.trim().toUpperCase().replace(' ', '_').replace('-', '_');
        for (AssetType type : values()) {
            if (type.name().equals(normalized)) {
                return type;
            }
        }
        return switch (normalized) {
            case "TOWER", "TOWERS", "EVACUATION_TOWERS", "TRANSMISSION_TOWER", "GANTRY" -> EVACUATION_TOWER;
            case "TURBINE", "WIND_TURBINE", "WEC" -> WTG;
            case "SUB", "PSS", "SUBSTATIONS", "GRID_SUBSTATION" -> SUBSTATION;
            case "BOREHOLE", "GEOTECH", "SURVEY" -> SURVEY_POINT;
            case "PARCELS", "LAND", "CADASTRAL_PARCEL", "PLOT" -> PARCEL;
            case "RESTRICTED", "RESTRICTED_AREAS", "EXCLUSION", "EXCLUSION_ZONE" -> RESTRICTED_AREA;
            case "LINE", "REFERENCE_LINES", "ROAD", "HT_LINE" -> REFERENCE_LINE;
            default -> UNKNOWN;
        };
    }
}
