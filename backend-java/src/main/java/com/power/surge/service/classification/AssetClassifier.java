package com.power.surge.service.classification;

import com.power.surge.domain.AssetType;
import com.power.surge.domain.LineType;
import com.power.surge.domain.WtgStatus;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

/**
 * Resolves the {@link AssetType} of an imported placemark using an ordered rule chain.
 *
 * <p>Chain order, first match wins:</p>
 * <ol>
 *   <li>an explicit {@code assetType} property on the feature;</li>
 *   <li>a KML folder name, evaluated one path segment at a time from the leaf folder upward;</li>
 *   <li>the placemark name matched against configured ID patterns;</li>
 *   <li>{@link AssetType#UNKNOWN}.</li>
 * </ol>
 *
 * <p>The fallback is deliberately {@code UNKNOWN} and never {@code WTG}. Defaulting unmatched
 * placemarks to turbines is what caused evacuation towers to be persisted as 3.0 MW WTGs and fed
 * into the optimiser.</p>
 */
@Component
public class AssetClassifier {

    /** Folder path segments that carry no classification meaning and are skipped during the walk. */
    private static final List<String> IGNORED_SEGMENTS =
            List.of("nom du document", "sheet1", "document", "folder", "line features", "untitled");

    /**
     * Segments that mark the start of an embedded copy of another document.
     *
     * <p>Google Earth writes "My Places" when a whole tree is pasted inside another one, which the
     * reference file does three times. Folders <em>above</em> such a marker belong to a different
     * document and must not classify anything below it — without this boundary a polygon in
     * "G.O.Boundary" inherits "PSS Land final" from the outer copy and is read as a land parcel.</p>
     */
    private static final List<String> NESTING_BOUNDARIES = List.of("my places");

    /** Folder paths are joined with " / "; a bare slash inside a name (e.g. "220/11KV") is not a separator. */
    private static final Pattern PATH_SEPARATOR = Pattern.compile("\\s+/\\s+");

    private final AssetClassificationRules defaultRules;

    public AssetClassifier() {
        this(AssetClassificationRules.defaults());
    }

    public AssetClassifier(AssetClassificationRules defaultRules) {
        this.defaultRules = defaultRules;
    }

    public ClassificationResult classify(String externalId, String kmlFolderPath, String explicitType) {
        return classify(externalId, kmlFolderPath, explicitType, defaultRules);
    }

    public ClassificationResult classify(
            String externalId,
            String kmlFolderPath,
            String explicitType,
            AssetClassificationRules rules
    ) {
        String id = externalId == null ? "" : externalId.trim();
        List<String> segments = folderSegmentsLeafFirst(kmlFolderPath);

        // Rule 1 — explicit property wins outright.
        AssetType explicit = AssetType.fromNullable(explicitType);
        if (explicit != AssetType.UNKNOWN) {
            return new ClassificationResult(
                    explicit, statusFor(explicit, segments, rules), ClassificationResult.Rule.EXPLICIT_PROPERTY, explicitType.trim());
        }

        // Rule 2 — folder keywords, leaf first. Survey is tested before substation so that a
        // folder such as "Anantapur PSS_Borehole.kmz" resolves to a survey marker.
        for (String segment : segments) {
            String lower = segment.toLowerCase(Locale.ROOT);
            if (containsAny(lower, rules.surveyFolderKeywords())) {
                return resolved(AssetType.SURVEY_POINT, segments, rules, ClassificationResult.Rule.KML_FOLDER, segment);
            }
            if (containsAny(lower, rules.towerFolderKeywords())) {
                return resolved(AssetType.EVACUATION_TOWER, segments, rules, ClassificationResult.Rule.KML_FOLDER, segment);
            }
            if (containsAny(lower, rules.substationFolderKeywords())) {
                return resolved(AssetType.SUBSTATION, segments, rules, ClassificationResult.Rule.KML_FOLDER, segment);
            }
            if (containsAny(lower, rules.wtgFolderKeywords())) {
                return resolved(AssetType.WTG, segments, rules, ClassificationResult.Rule.KML_FOLDER, segment);
            }
        }

        // Rule 3 — ID patterns. Order mirrors the folder pass.
        if (!id.isEmpty()) {
            if (rules.surveyIdPattern().matcher(id).find()) {
                return resolved(AssetType.SURVEY_POINT, segments, rules, ClassificationResult.Rule.ID_PATTERN, id);
            }
            if (rules.towerIdPattern().matcher(id).find()) {
                return resolved(AssetType.EVACUATION_TOWER, segments, rules, ClassificationResult.Rule.ID_PATTERN, id);
            }
            if (rules.substationIdPattern().matcher(id).find()) {
                return resolved(AssetType.SUBSTATION, segments, rules, ClassificationResult.Rule.ID_PATTERN, id);
            }
            if (rules.wtgIdPattern().matcher(id).find()) {
                return resolved(AssetType.WTG, segments, rules, ClassificationResult.Rule.ID_PATTERN, id);
            }
        }

        // Rule 4 — no guessing.
        return ClassificationResult.unresolved(id);
    }

    /**
     * Resolves a Polygon placemark to {@link AssetType#PARCEL} or {@link AssetType#RESTRICTED_AREA}.
     *
     * <p>Same chain as points: explicit property, then folder leaf-first, then name. Restricted is
     * tested before parcel because an exclusion zone misfiled as a parcel would be routed straight
     * through, whereas a parcel misfiled as an exclusion merely costs a detour.</p>
     */
    public ClassificationResult classifyPolygon(String name, String kmlFolderPath, String explicitType) {
        return classifyPolygon(name, kmlFolderPath, explicitType, defaultRules);
    }

    public ClassificationResult classifyPolygon(
            String name, String kmlFolderPath, String explicitType, AssetClassificationRules rules) {

        String id = name == null ? "" : name.trim();

        AssetType explicit = AssetType.fromNullable(explicitType);
        if (explicit == AssetType.PARCEL || explicit == AssetType.RESTRICTED_AREA) {
            return new ClassificationResult(explicit, WtgStatus.UNKNOWN,
                    ClassificationResult.Rule.EXPLICIT_PROPERTY, explicitType.trim());
        }

        for (String segment : folderSegmentsLeafFirst(kmlFolderPath)) {
            String lower = segment.toLowerCase(Locale.ROOT);
            if (containsAny(lower, rules.restrictedFolderKeywords())) {
                return area(AssetType.RESTRICTED_AREA, ClassificationResult.Rule.KML_FOLDER, segment);
            }
            if (containsAny(lower, rules.parcelFolderKeywords())) {
                return area(AssetType.PARCEL, ClassificationResult.Rule.KML_FOLDER, segment);
            }
        }

        if (!id.isEmpty()) {
            if (rules.restrictedNamePattern().matcher(id).find()) {
                return area(AssetType.RESTRICTED_AREA, ClassificationResult.Rule.ID_PATTERN, id);
            }
            if (rules.parcelNamePattern().matcher(id).find()) {
                return area(AssetType.PARCEL, ClassificationResult.Rule.ID_PATTERN, id);
            }
        }

        // "Untitled Polygon", "G.O.Boundary" and similar reach the import preview unresolved.
        return ClassificationResult.unresolved(id);
    }

    /**
     * Resolves a LineString placemark to a {@link LineType}.
     *
     * <p>Folder is evaluated before name deliberately. The surveyor drew most of the PCN route with
     * Google Earth's measuring tool, so 15 genuine route segments are named "Path Measure"; treating
     * that name as authoritative would discard the estimated route itself. The measurement pattern
     * therefore only fires when the enclosing folders say nothing useful.</p>
     */
    public LineClassification classifyLine(String name, String kmlFolderPath, String explicitType) {
        return classifyLine(name, kmlFolderPath, explicitType, defaultRules);
    }

    public LineClassification classifyLine(
            String name, String kmlFolderPath, String explicitType, AssetClassificationRules rules) {

        String id = name == null ? "" : name.trim();

        LineType explicit = LineType.fromNullable(explicitType);
        if (explicit != LineType.UNKNOWN) {
            return new LineClassification(explicit, ClassificationResult.Rule.EXPLICIT_PROPERTY, explicitType.trim());
        }

        for (String segment : folderSegmentsLeafFirst(kmlFolderPath)) {
            String lower = segment.toLowerCase(Locale.ROOT);
            if (containsAny(lower, rules.watercourseFolderKeywords())) {
                return new LineClassification(LineType.WATERCOURSE, ClassificationResult.Rule.KML_FOLDER, segment);
            }
            if (containsAny(lower, rules.roadFolderKeywords())) {
                return new LineClassification(LineType.ROAD, ClassificationResult.Rule.KML_FOLDER, segment);
            }
            if (containsAny(lower, rules.routeFolderKeywords())) {
                return new LineClassification(LineType.EVACUATION_ROUTE, ClassificationResult.Rule.KML_FOLDER, segment);
            }
            if (containsAny(lower, rules.htLineFolderKeywords())) {
                return new LineClassification(LineType.HT_LINE, ClassificationResult.Rule.KML_FOLDER, segment);
            }
        }

        if (!id.isEmpty()) {
            if (rules.roadNamePattern().matcher(id).find()) {
                return new LineClassification(LineType.ROAD, ClassificationResult.Rule.ID_PATTERN, id);
            }
            if (rules.htLineNamePattern().matcher(id).find()) {
                return new LineClassification(LineType.HT_LINE, ClassificationResult.Rule.ID_PATTERN, id);
            }
            if (rules.watercourseNamePattern().matcher(id).find()) {
                return new LineClassification(LineType.WATERCOURSE, ClassificationResult.Rule.ID_PATTERN, id);
            }
            if (rules.measurementNamePattern().matcher(id).matches()) {
                return new LineClassification(LineType.MEASUREMENT, ClassificationResult.Rule.ID_PATTERN, id);
            }
        }

        return new LineClassification(LineType.UNKNOWN, ClassificationResult.Rule.UNRESOLVED, id);
    }

    /** Outcome of classifying a linear feature. */
    public record LineClassification(LineType lineType, ClassificationResult.Rule matchedRule, String evidence) {
    }

    private static ClassificationResult area(AssetType type, ClassificationResult.Rule rule, String evidence) {
        return new ClassificationResult(type, WtgStatus.UNKNOWN, rule, evidence);
    }

    /**
     * Collapses separator noise so that {@code KS-38_S3}, {@code KS 38 S3} and {@code ks38s3}
     * deduplicate to a single logical asset.
     */
    public String normaliseId(String externalId) {
        if (externalId == null) {
            return "";
        }
        return externalId.trim().toUpperCase(Locale.ROOT).replaceAll("[\\s_\\-.]", "");
    }

    private ClassificationResult resolved(
            AssetType type,
            List<String> segments,
            AssetClassificationRules rules,
            ClassificationResult.Rule rule,
            String evidence
    ) {
        return new ClassificationResult(type, statusFor(type, segments, rules), rule, evidence);
    }

    private WtgStatus statusFor(AssetType type, List<String> segments, AssetClassificationRules rules) {
        if (type != AssetType.WTG) {
            return WtgStatus.UNKNOWN;
        }
        for (String segment : segments) {
            String lower = segment.toLowerCase(Locale.ROOT);
            for (AssetClassificationRules.StatusRule statusRule : rules.statusRules()) {
                if (lower.contains(statusRule.keyword())) {
                    return statusRule.status();
                }
            }
        }
        return WtgStatus.UNKNOWN;
    }

    /**
     * Splits a {@code A / B / C} folder path into segments ordered leaf first, dropping structural
     * noise. Survey exports frequently nest a copy of the whole tree under an unrelated folder, so
     * the nearest enclosing folder is by far the most reliable signal.
     */
    private List<String> folderSegmentsLeafFirst(String kmlFolderPath) {
        List<String> segments = new ArrayList<>();
        if (kmlFolderPath == null || kmlFolderPath.isBlank()) {
            return segments;
        }
        // Split on " / " only. Folder names legitimately contain bare slashes, e.g. "220/11KV".
        String[] parts = PATH_SEPARATOR.split(kmlFolderPath);
        for (int i = parts.length - 1; i >= 0; i--) {
            String segment = parts[i].trim();
            if (segment.isEmpty()) {
                continue;
            }
            String lower = segment.toLowerCase(Locale.ROOT);
            if (NESTING_BOUNDARIES.contains(lower)) {
                break;
            }
            if (IGNORED_SEGMENTS.contains(lower)) {
                continue;
            }
            segments.add(segment);
        }
        return segments;
    }

    private static boolean containsAny(String haystack, List<String> needles) {
        for (String needle : needles) {
            if (haystack.contains(needle)) {
                return true;
            }
        }
        return false;
    }
}
