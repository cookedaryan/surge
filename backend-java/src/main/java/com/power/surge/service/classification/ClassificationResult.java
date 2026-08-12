package com.power.surge.service.classification;

import com.power.surge.domain.AssetType;
import com.power.surge.domain.WtgStatus;

/**
 * Outcome of classifying a single placemark.
 *
 * @param assetType   what the feature was resolved to
 * @param status      turbine lifecycle status; always {@link WtgStatus#UNKNOWN} for non-WTG types
 * @param matchedRule which rule in the chain fired, for display in the import preview
 * @param evidence    the concrete value that matched, e.g. the folder segment or the ID
 */
public record ClassificationResult(
        AssetType assetType,
        WtgStatus status,
        Rule matchedRule,
        String evidence
) {

    /** The ordered rule chain. Earlier constants take precedence over later ones. */
    public enum Rule {
        /** An explicit {@code assetType} / {@code type} / {@code layer} property was present. */
        EXPLICIT_PROPERTY,
        /** A KML folder name on the placemark's path matched a keyword. */
        KML_FOLDER,
        /** The placemark name matched a configured ID pattern. */
        ID_PATTERN,
        /** Nothing matched. Requires a human decision. */
        UNRESOLVED
    }

    public static ClassificationResult unresolved(String externalId) {
        return new ClassificationResult(AssetType.UNKNOWN, WtgStatus.UNKNOWN, Rule.UNRESOLVED, externalId);
    }

    public boolean isResolved() {
        return assetType != AssetType.UNKNOWN;
    }
}
