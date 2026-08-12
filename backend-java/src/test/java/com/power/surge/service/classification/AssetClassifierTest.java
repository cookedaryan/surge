package com.power.surge.service.classification;

import com.power.surge.domain.AssetType;
import com.power.surge.domain.WtgStatus;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Cases are taken verbatim from the Uravakonda Estimated PCN route KMZ.
 */
class AssetClassifierTest {

    private static final String TOWER_FOLDER =
            "Uravakonda Updated KMZ File / HT Lines / Gantry - AP34 / Sheet1";
    private static final String APPROVED_FOLDER =
            "Uravakonda Updated KMZ File / Approved";
    private static final String CANCELLED_FOLDER =
            "Uravakonda Updated KMZ File / Cancel Location";
    private static final String PSS_FOLDER =
            "Uravakonda Updated KMZ File / HT Lines / Uravakonda site-EHV Lines / PSS Land";
    private static final String BOREHOLE_FOLDER =
            "Uravakonda Updated KMZ File / PSS Land final / Anantapur PSS_Borehole.kmz";

    private final AssetClassifier classifier = new AssetClassifier();

    // --- Rule 3: ID patterns -------------------------------------------------

    @ParameterizedTest
    @ValueSource(strings = {"KS67_S1", "KS-38_S3", "KS 24 S2", "KS42P_S2", "KS55",
            "SUR0001_S2", "SUR003_S4", "VAJ042_S2", "VAJ051_S1"})
    @DisplayName("turbine IDs resolve to WTG on the ID pattern alone")
    void turbineIdsResolveToWtg(String externalId) {
        ClassificationResult result = classifier.classify(externalId, null, null);

        assertThat(result.assetType()).isEqualTo(AssetType.WTG);
        assertThat(result.matchedRule()).isEqualTo(ClassificationResult.Rule.ID_PATTERN);
    }

    @ParameterizedTest
    @ValueSource(strings = {"2/1", "2/4", "15/11", "20/12", "10/1", "AP1", "AP34", "GANTRY"})
    @DisplayName("tower IDs resolve to EVACUATION_TOWER on the ID pattern alone")
    void towerIdsResolveToTower(String externalId) {
        ClassificationResult result = classifier.classify(externalId, null, null);

        assertThat(result.assetType()).isEqualTo(AssetType.EVACUATION_TOWER);
        assertThat(result.matchedRule()).isEqualTo(ClassificationResult.Rule.ID_PATTERN);
    }

    @ParameterizedTest
    @ValueSource(strings = {"Mopidi PSS", "MOPIDI PSS", "Ragulapadu 220/11KV Substation",
            "SUZLON OMS AND SUBSTATION"})
    void substationNamesResolveToSubstation(String externalId) {
        assertThat(classifier.classify(externalId, null, null).assetType())
                .isEqualTo(AssetType.SUBSTATION);
    }

    @ParameterizedTest
    @ValueSource(strings = {"BH-1", "CBR-2", "ERT-5", "PLT-1", "TP-1", "TRT-1"})
    void geotechnicalMarkersResolveToSurveyPoint(String externalId) {
        assertThat(classifier.classify(externalId, null, null).assetType())
                .isEqualTo(AssetType.SURVEY_POINT);
    }

    @Test
    @DisplayName("a voltage-class substation name is not mistaken for a section/index tower ID")
    void voltageClassIsNotATowerId() {
        assertThat(classifier.classify("Ragulapadu 220/11KV Substation", null, null).assetType())
                .isEqualTo(AssetType.SUBSTATION);
    }

    // --- Rule 2: folder keywords --------------------------------------------

    @Test
    @DisplayName("the enclosing folder resolves towers whose names are bare numbers")
    void folderResolvesTowersFromParentSegment() {
        ClassificationResult result = classifier.classify("GANTRY", TOWER_FOLDER, null);

        assertThat(result.assetType()).isEqualTo(AssetType.EVACUATION_TOWER);
        assertThat(result.matchedRule()).isEqualTo(ClassificationResult.Rule.KML_FOLDER);
        assertThat(result.evidence()).isEqualTo("Gantry - AP34");
    }

    @Test
    @DisplayName("folder beats ID pattern")
    void folderTakesPrecedenceOverIdPattern() {
        // KS90 looks like a turbine, but it sits in the gantry folder.
        ClassificationResult result = classifier.classify("KS90_S1", TOWER_FOLDER, null);

        assertThat(result.assetType()).isEqualTo(AssetType.EVACUATION_TOWER);
        assertThat(result.matchedRule()).isEqualTo(ClassificationResult.Rule.KML_FOLDER);
    }

    @Test
    @DisplayName("survey keywords are tested before substation keywords")
    void boreholeFolderBeatsPssKeyword() {
        ClassificationResult result = classifier.classify("BH-1", BOREHOLE_FOLDER, null);

        assertThat(result.assetType()).isEqualTo(AssetType.SURVEY_POINT);
        assertThat(result.evidence()).isEqualTo("Anantapur PSS_Borehole.kmz");
    }

    @Test
    void pssLandFolderResolvesSubstations() {
        assertThat(classifier.classify("Mopidi PSS", PSS_FOLDER, null).assetType())
                .isEqualTo(AssetType.SUBSTATION);
    }

    @Test
    @DisplayName("the nearest enclosing folder wins when the tree is nested inside itself")
    void leafFolderWinsOverAncestors() {
        String selfNestedPath = "Uravakonda Updated KMZ File / Cancel Location / My Places "
                + "/ Uravakonda Updated KMZ File / Approved";

        ClassificationResult result = classifier.classify("KS67_S1", selfNestedPath, null);

        assertThat(result.assetType()).isEqualTo(AssetType.WTG);
        assertThat(result.status()).isEqualTo(WtgStatus.APPROVED);
    }

    // --- Rule 1: explicit property ------------------------------------------

    @Test
    void explicitPropertyBeatsFolderAndId() {
        ClassificationResult result = classifier.classify("KS67_S1", TOWER_FOLDER, "SUBSTATION");

        assertThat(result.assetType()).isEqualTo(AssetType.SUBSTATION);
        assertThat(result.matchedRule()).isEqualTo(ClassificationResult.Rule.EXPLICIT_PROPERTY);
    }

    @Test
    void explicitPropertyAcceptsCommonAliases() {
        assertThat(classifier.classify("X", null, "tower").assetType())
                .isEqualTo(AssetType.EVACUATION_TOWER);
    }

    // --- Rule 4: the fallback that fixes the original defect ------------------

    @ParameterizedTest
    @ValueSource(strings = {"Feeder 4", "Penna River", "P.A.B.R Reservoir", "A", "B", "C", "D",
            "Untitled Placemark"})
    @DisplayName("unrecognised placemarks are UNKNOWN, never WTG")
    void unrecognisedPlacemarksAreUnknown(String externalId) {
        ClassificationResult result = classifier.classify(externalId, "Uravakonda PCN", null);

        assertThat(result.assetType())
                .as("regression guard: the original defect defaulted every unmatched feature to WTG")
                .isEqualTo(AssetType.UNKNOWN);
        assertThat(result.matchedRule()).isEqualTo(ClassificationResult.Rule.UNRESOLVED);
    }

    // --- Status derivation ---------------------------------------------------

    @ParameterizedTest
    @CsvSource({
            "Approved,APPROVED,true",
            "Registration,REGISTRATION,true",
            "proposed,PROPOSED,true",
            "To be Shifting,TO_BE_SHIFTED,false",
            "Low AEP,LOW_AEP,false",
            "Cancel Location,CANCELLED,false"
    })
    void statusIsDerivedFromFolder(String folder, WtgStatus expected, boolean optimisable) {
        ClassificationResult result =
                classifier.classify("KS67_S1", "Uravakonda Updated KMZ File / " + folder, null);

        assertThat(result.assetType()).isEqualTo(AssetType.WTG);
        assertThat(result.status()).isEqualTo(expected);
        assertThat(result.status().isOptimisable()).isEqualTo(optimisable);
    }

    @Test
    void nonTurbineAssetsCarryNoStatus() {
        assertThat(classifier.classify("GANTRY", TOWER_FOLDER, null).status())
                .isEqualTo(WtgStatus.UNKNOWN);
    }

    @Test
    void cancelledTurbinesAreExcludedFromOptimisation() {
        ClassificationResult result = classifier.classify("KS82_S2", CANCELLED_FOLDER, null);

        assertThat(result.status()).isEqualTo(WtgStatus.CANCELLED);
        assertThat(result.status().isOptimisable()).isFalse();
    }

    @Test
    void approvedTurbinesFeedTheOptimiser() {
        assertThat(classifier.classify("KS67_S1", APPROVED_FOLDER, null).status().isOptimisable())
                .isTrue();
    }

    // --- ID normalisation for deduplication ----------------------------------

    @ParameterizedTest
    @CsvSource({
            "KS-38_S3,KS38S3",
            "KS 24 S2,KS24S2",
            "KS51 S2,KS51S2",
            "ks51_s2,KS51S2",
            "SUR0001_S2,SUR0001S2"
    })
    void separatorNoiseIsCollapsedForDeduplication(String input, String expected) {
        assertThat(classifier.normaliseId(input)).isEqualTo(expected);
    }
}
