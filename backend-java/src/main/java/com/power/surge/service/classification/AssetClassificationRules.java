package com.power.surge.service.classification;

import com.power.surge.domain.WtgStatus;

import java.util.List;
import java.util.regex.Pattern;

/**
 * Configurable pattern set driving {@link AssetClassifier}.
 *
 * <p>Defaults are derived from the Uravakonda PCN survey KMZ, which is representative of the
 * India wind-farm survey exports SURGE ingests:</p>
 *
 * <ul>
 *   <li>Turbines are prefixed {@code KS}, {@code SUR} or {@code VAJ} and suffixed with a siting
 *       revision ({@code KS67_S1}, {@code KS-38_S3}, {@code KS 24 S2}, {@code KS42P_S2}).</li>
 *   <li>Towers are numbered {@code <section>/<index>} ({@code 2/1}, {@code 20/12}), angle points
 *       {@code AP1}..{@code AP34}, or the line-terminating {@code GANTRY}.</li>
 *   <li>Substations are named {@code ... PSS}, {@code ... Substation}, or carry a voltage class
 *       such as {@code 220/11KV}.</li>
 *   <li>Geotechnical markers are prefixed {@code BH}, {@code CBR}, {@code ERT}, {@code PLT},
 *       {@code TP} or {@code TRT}.</li>
 * </ul>
 *
 * <p>Folder keywords are matched against a single path segment at a time, walking from the leaf
 * folder upward. Survey keywords are evaluated before substation keywords so that a folder named
 * {@code Anantapur PSS_Borehole.kmz} resolves to survey rather than substation.</p>
 */
public record AssetClassificationRules(
        List<String> wtgFolderKeywords,
        List<String> towerFolderKeywords,
        List<String> substationFolderKeywords,
        List<String> surveyFolderKeywords,
        Pattern wtgIdPattern,
        Pattern towerIdPattern,
        Pattern substationIdPattern,
        Pattern surveyIdPattern,
        List<StatusRule> statusRules,

        // --- Polygon rules -------------------------------------------------
        List<String> restrictedFolderKeywords,
        List<String> parcelFolderKeywords,
        Pattern restrictedNamePattern,
        Pattern parcelNamePattern,

        // --- LineString rules ----------------------------------------------
        List<String> roadFolderKeywords,
        List<String> htLineFolderKeywords,
        List<String> routeFolderKeywords,
        List<String> watercourseFolderKeywords,
        Pattern roadNamePattern,
        Pattern htLineNamePattern,
        Pattern watercourseNamePattern,
        Pattern measurementNamePattern
) {

    private static final int FLAGS = Pattern.CASE_INSENSITIVE;

    /** A folder-name keyword mapped to the turbine status it implies. Order is significant. */
    public record StatusRule(String keyword, WtgStatus status) {
    }

    public static AssetClassificationRules defaults() {
        return new AssetClassificationRules(
                List.of("turbine", "wtg", "wec", "weg", "wind turbine", "wtg location", "wtg locations", "approved", "proposed", "registration",
                        "low aep", "cancel", "shifting", "micrositing", "micro siting", "wind farm", "wind park"),
                List.of("gantry", "tower", "towers", "angle point", "angle points", "evacuation", "transmission",
                        "ht line", "ehv", "pylon", "pole", "poles", "line section", "structure", "structures"),
                List.of("pss", "substation", "substations", "s/s", "switchyard", "pgcil", "ctu", "pooling", "dpss", "bay", "grid"),
                List.of("borehole", "geotech", "soil investigation", "survey point"),

                // WTG-001 | WTG1 | TURBINE-1 | WEC-1 | WEG-1 | KS67_S1 | SUR0001 | VAJ051 | LOC-1
                Pattern.compile("^(\\bWTG\\b|\\bTURBINE\\b|\\bWEC\\b|\\bWEG\\b|KS|SUR|VAJ|LOC)[\\s_-]*\\d+", FLAGS),

                // 2/1 | 15/11 | 20/12 | AP1 | AP-34 | GANTRY | TOWER-7 | TWR-01 | POLE-1 | STR-1
                Pattern.compile("^(\\d+\\s*/\\s*\\d+|AP[\\s_-]*\\d+|GANTRY|TOWER[\\s_-]*\\d+|TWR[\\s_-]*\\d+|POLE[\\s_-]*\\d+|STR[\\s_-]*\\d+|LOC[\\s_-]*\\d+\\s*/\\s*\\d+)$", FLAGS),

                // Mopidi PSS | Ragulapadu 220/11KV Substation | SUZLON OMS AND SUBSTATION | SUB-1 | DPSS
                Pattern.compile("(\\bPSS\\b|SUBSTATION|\\bS/S\\b|\\bSUB\\b|SWITCHYARD|POOLING|DPSS|\\d+\\s*/\\s*\\d+\\s*KV)", FLAGS),

                // BH-1 | CBR-2 | ERT-5 | PLT-1 | TP-1 | TRT-1
                Pattern.compile("^(BH|CBR|ERT|PLT|TP|TRT)[\\s_-]*\\d+$", FLAGS),

                // Longest / most specific keyword first.
                List.of(
                        new StatusRule("cancel location", WtgStatus.CANCELLED),
                        new StatusRule("to be shifting", WtgStatus.TO_BE_SHIFTED),
                        new StatusRule("low aep", WtgStatus.LOW_AEP),
                        new StatusRule("registration", WtgStatus.REGISTRATION),
                        new StatusRule("approved", WtgStatus.APPROVED),
                        new StatusRule("proposed", WtgStatus.PROPOSED),
                        new StatusRule("shifting", WtgStatus.TO_BE_SHIFTED),
                        new StatusRule("cancel", WtgStatus.CANCELLED)
                ),

                // --- Polygons ---------------------------------------------
                List.of("river", "reservoir", "canal", "lake", "tank", "water", "forest",
                        "sanctuary", "reserve", "wildlife", "village", "settlement", "radar",
                        "restricted", "exclusion", "buffer"),
                List.of("parcel", "cadastral", "land", "acquisition", "plot", "survey no"),

                // Penna River | Penna Ahobilam Balancing Reservoir | Kutch Flamingo Sanctuary
                Pattern.compile(
                        "(RIVER|RESERVOIR|CANAL|\\bLAKE\\b|\\bTANK\\b|\\bNALA\\b|FOREST|SANCTUARY|"
                                + "WILDLIFE|RESERVE|SETTLEMENT|RADAR|BUFFER|SETBACK)", FLAGS),
                // PSS Land | PSS Land = 9.21 Acres | Survey No 143/2
                Pattern.compile("(\\bLAND\\b|PARCEL|\\bPLOT\\b|ACRES?\\b|SURVEY\\s*NO)", FLAGS),

                // --- LineStrings ------------------------------------------
                List.of("road", "highway", "b.t.road", "bt road", "track"),
                List.of("ht line", "ehv", "gantry", "transmission", "power line"),
                List.of("pcn", "evacuation", "collector", "feeder"),
                List.of("river", "canal", "reservoir", "water", "stream"),

                // NH- 42 | SH-42 to Mulagiripalle | ... to Racharla B.T.Road
                Pattern.compile("(^\\s*(NH|SH)[\\s-]*\\d+|\\bROAD\\b|HIGHWAY|\\bB\\.?T\\.?\\s*ROAD)", FLAGS),
                // HT LINE | 133 KV | 220KV
                Pattern.compile("(\\bHT\\s*LINE\\b|\\d+\\s*KV\\b|TRANSMISSION)", FLAGS),
                Pattern.compile("(RIVER|CANAL|STREAM|RESERVOIR)", FLAGS),
                // Google Earth measuring-tool leftovers.
                Pattern.compile("^(PATH\\s*MEASURE|POLYLINE|UNTITLED\\s*(PATH|LINE|POLYGON))\\s*\\d*$", FLAGS)
        );
    }
}
