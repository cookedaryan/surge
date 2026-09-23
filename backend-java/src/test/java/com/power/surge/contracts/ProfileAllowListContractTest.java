package com.power.surge.contracts;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.dto.client.python.PythonOptimisationRequest;
import com.power.surge.dto.client.python.PythonProfileSelection;
import com.power.surge.dto.job.CreateOptimizationJobRequest;
import com.power.surge.service.OptimisationProfile;
import com.power.surge.service.ScenarioProfile;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.lang.reflect.RecordComponent;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * WP3-5: Java's profile allow-list and its serialisation, held to the shared contract.
 *
 * <p>Reads {@code contracts/profiles/allow-list.json} and {@code contracts/fixtures/request/} rather
 * than restating them. Java's copy of the allow-list is a duplicate of Python's by necessity — it
 * has to refuse an unknown ID without asking Python — and a duplicate that nothing compares is a
 * duplicate that drifts. A CCR that adds a profile or a version fails here instead.
 */
class ProfileAllowListContractTest {

    private static final Path ALLOW_LIST =
            Path.of("..", "contracts", "profiles", "allow-list.json");

    private static final Path SELECTION_FIXTURE =
            Path.of("..", "contracts", "fixtures", "request", "profile-selection.json");

    private static final Path SCHEMA =
            Path.of("..", "contracts", "schemas", "v1-request-profile.schema.json");

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> allowListProfiles() throws IOException {
        Map<String, Object> document = MAPPER.readValue(Files.readString(ALLOW_LIST), new TypeReference<>() {});
        return (List<Map<String, Object>>) document.get("profiles");
    }

    // --- The allow-list itself ------------------------------------------------------------

    @Test
    void javaHoldsExactlyTheProfilesTheContractAllows() throws IOException {
        Set<String> published = allowListProfiles().stream()
                .map(profile -> (String) profile.get("id"))
                .collect(Collectors.toSet());

        Set<String> held = Stream.of(OptimisationProfile.values())
                .map(OptimisationProfile::wireId)
                .collect(Collectors.toSet());

        // Both directions. A missing profile means a client is refused something it was promised;
        // an extra one means Java can send an ID Python has no definition for.
        assertThat(held).containsExactlyInAnyOrderElementsOf(published);
    }

    @Test
    void everyProfileAllowsExactlyThePublishedVersions() throws IOException {
        for (Map<String, Object> published : allowListProfiles()) {
            String id = (String) published.get("id");
            @SuppressWarnings("unchecked")
            List<String> versions = (List<String>) published.get("versions");

            assertThat(OptimisationProfile.fromClientId(id).allowedVersions())
                    .as("versions for %s", id)
                    .containsExactlyInAnyOrderElementsOf(versions);
        }
    }

    @Test
    void everyProfileCarriesTheScenarioLabelTheContractPairsItWith() throws IOException {
        for (Map<String, Object> published : allowListProfiles()) {
            String id = (String) published.get("id");

            // C1 rejects a request whose scenario does not match its profile
            // (PROFILE_SCENARIO_MISMATCH), so a wrong label here is a run that dies at the far end.
            assertThat(OptimisationProfile.fromClientId(id).scenarioLabel())
                    .as("scenario label for %s", id)
                    .isEqualTo(published.get("scenario_label"));
        }
    }

    @Test
    void theScenarioLabelResolvesBackToTheSameSetOfScoringWeights() {
        // The label is not decoration: it also picks the V0 ScenarioProfile. If the two ever named
        // different things, one request would carry a profile and the cost bias of another.
        for (OptimisationProfile profile : OptimisationProfile.values()) {
            assertThat(ScenarioProfile.forScenario(profile.scenarioLabel()).scenario())
                    .as("scenario round trip for %s", profile.wireId())
                    .isEqualTo(profile.scenarioLabel());
        }
    }

    // --- Serialisation --------------------------------------------------------------------

    @Test
    void theBalancedSelectionSerialisesToTheContractFixture() throws IOException {
        Map<String, Object> fixture =
                MAPPER.readValue(Files.readString(SELECTION_FIXTURE), new TypeReference<>() {});

        Map<String, Object> produced = MAPPER.convertValue(
                OptimisationProfile.BALANCED.selection(), new TypeReference<>() {});

        assertThat(produced).isEqualTo(fixture);
    }

    @Test
    void everySelectionCarriesExactlyTheFieldsTheSchemaRequires() throws IOException {
        Map<String, Object> schema = MAPPER.readValue(Files.readString(SCHEMA), new TypeReference<>() {});
        @SuppressWarnings("unchecked")
        Set<String> properties = ((Map<String, Object>) schema.get("properties")).keySet();

        // additionalProperties is false in the schema, so an extra field would be rejected by
        // Python rather than ignored, and a missing one is a required field absent.
        assertThat(schema.get("additionalProperties")).isEqualTo(Boolean.FALSE);

        for (OptimisationProfile profile : OptimisationProfile.values()) {
            Map<String, Object> produced =
                    MAPPER.convertValue(profile.selection(), new TypeReference<>() {});

            assertThat(produced.keySet())
                    .as("fields sent for %s", profile.wireId())
                    .containsExactlyInAnyOrderElementsOf(properties);
            assertThat(produced.get("id")).isEqualTo(profile.wireId());
            assertThat(produced.get("version")).isEqualTo(profile.currentVersion());
        }
    }

    @Test
    void aSelectionSurvivesADecodeAndReEncode() throws IOException {
        for (OptimisationProfile profile : OptimisationProfile.values()) {
            String written = MAPPER.writeValueAsString(profile.selection());
            PythonProfileSelection read = MAPPER.readValue(written, PythonProfileSelection.class);

            assertThat(read).isEqualTo(profile.selection());
            assertThat(MAPPER.writeValueAsString(read)).isEqualTo(written);
        }
    }

    @Test
    void anAbsentProfileIsAbsentFromTheJsonRatherThanNull() throws IOException {
        // C1: absent means V0. An explicit null would read the same way in Python today, but the
        // contract and its fixtures are written about absence, and V0 requests must stay V0.
        PythonOptimisationRequest v0 = new PythonOptimisationRequest(
                "job-1", "project-1", ScenarioProfile.BALANCED, null,
                Map.of(), Map.of(), Map.of(), Map.of(), Map.of(), Map.of(), Map.of(), Map.of());

        Map<String, Object> written = MAPPER.convertValue(v0, new TypeReference<>() {});

        assertThat(written).doesNotContainKey("profile");
    }

    @Test
    void aChosenProfileIsSentUnderTheProfileKey() throws IOException {
        PythonOptimisationRequest withProfile = new PythonOptimisationRequest(
                "job-1", "project-1", ScenarioProfile.MINIMUM_COST,
                OptimisationProfile.MINIMUM_COST.selection(),
                Map.of(), Map.of(), Map.of(), Map.of(), Map.of(), Map.of(), Map.of(), Map.of());

        @SuppressWarnings("unchecked")
        Map<String, Object> written = MAPPER.convertValue(withProfile, Map.class);
        @SuppressWarnings("unchecked")
        Map<String, Object> profile = (Map<String, Object>) written.get("profile");

        assertThat(profile).containsExactlyInAnyOrderEntriesOf(Map.of("id", "minimum_cost", "version", "1"));
        // The pair C1 checks together.
        assertThat(written.get("scenario")).isEqualTo(ScenarioProfile.MINIMUM_COST);
    }

    // --- What the browser may ask for -----------------------------------------------------

    @Test
    void theBrowserNamesAProfileAndNothingElseAboutIt() throws IOException {
        CreateOptimizationJobRequest fromBrowser = MAPPER.readValue("""
                {
                  "algorithmType": "MULTI_OBJECTIVE_A_STAR",
                  "scenario": "Balanced",
                  "profileId": "balanced"
                }
                """, CreateOptimizationJobRequest.class);

        assertThat(fromBrowser.profileId()).isEqualTo("balanced");
        assertThat(OptimisationProfile.fromClientId(fromBrowser.profileId()))
                .isEqualTo(OptimisationProfile.BALANCED);

        // Enforced by there being no field to fill, not by rejecting one: Spring's mapper ignores
        // unknown keys, so a client that sends a version or a weight is not refused - it is simply
        // not heard. Java pins the version and Python owns the values.
        List<String> components = Stream.of(CreateOptimizationJobRequest.class.getRecordComponents())
                .map(RecordComponent::getName)
                .toList();
        assertThat(components).contains("profileId");
        assertThat(components).doesNotContain(
                "profileVersion", "profile", "profileDefinition", "terms", "weights");
    }

    @Test
    void aRequestWithoutAProfileStillReadsAsV0() throws IOException {
        CreateOptimizationJobRequest v0 = MAPPER.readValue("""
                {"algorithmType": "MULTI_OBJECTIVE_A_STAR", "scenario": "Balanced"}
                """, CreateOptimizationJobRequest.class);

        assertThat(v0.profileId()).isNull();
    }

    // --- Failing closed -------------------------------------------------------------------

    @Test
    void anUnknownProfileIsRefusedRatherThanTreatedAsBalanced() {
        List<String> refused = new ArrayList<>(List.of(
                "minimum_carbon",       // plausible, and not a profile
                "Balanced",             // the scenario label, not the ID
                "BALANCED",
                " balanced",
                "balanced ",
                "balanced-1",
                ""));
        refused.add(null);

        for (String id : refused) {
            assertThatThrownBy(() -> OptimisationProfile.fromClientId(id))
                    .as("refusing '%s'", id)
                    .isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Test
    void theRefusalNamesWhatWasSentAndWhatIsAllowed() {
        assertThatThrownBy(() -> OptimisationProfile.fromClientId("minimum_carbon"))
                .hasMessageContaining("minimum_carbon")
                .hasMessageContaining("balanced");
    }

    @Test
    void aKnownProfileAtAnUnknownVersionIsRefused() {
        assertThat(OptimisationProfile.fromClientId("balanced", "1"))
                .isEqualTo(OptimisationProfile.BALANCED);

        for (String version : List.of("2", "0", "1.0", "v1", "")) {
            assertThatThrownBy(() -> OptimisationProfile.fromClientId("balanced", version))
                    .as("refusing version '%s'", version)
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContaining("balanced");
        }
    }

    @Test
    void javaPinsAVersionThatItsOwnAllowListAccepts() {
        // The version a client never sends. If currentVersion ever named something outside the
        // allow-list, Java would be generating requests it would itself refuse.
        for (OptimisationProfile profile : OptimisationProfile.values()) {
            assertThat(profile.allowsVersion(profile.currentVersion()))
                    .as("pinned version for %s", profile.wireId())
                    .isTrue();
        }
    }
}
