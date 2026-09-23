package com.power.surge.contracts;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.dto.client.python.PythonEffectiveProfile;
import com.power.surge.dto.job.EffectiveProfileResponse;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * WP3-7b: the C2 {@code effective_profile} block, read from the shared fixture.
 *
 * <p>Held to {@code contracts/fixtures/response/additive-blocks.json} and the C2 schema rather than
 * to a copy written here, so a CCR that changes the block fails in this file instead of drifting
 * into a column that quietly stops being filled.
 */
class EffectiveProfileContractTest {

    private static final Path FIXTURE =
            Path.of("..", "contracts", "fixtures", "response", "additive-blocks.json");

    private static final Path SCHEMA =
            Path.of("..", "contracts", "schemas", "v1-response-effective-profile.schema.json");

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @SuppressWarnings("unchecked")
    private static Map<String, Object> fixtureBlock() throws IOException {
        Map<String, Object> blocks =
                MAPPER.readValue(Files.readString(FIXTURE, StandardCharsets.UTF_8), new TypeReference<>() {});
        return (Map<String, Object>) blocks.get("effective_profile");
    }

    @Test
    void javaReadsEveryFieldTheFixturePublishes() throws IOException {
        PythonEffectiveProfile block =
                MAPPER.convertValue(fixtureBlock(), PythonEffectiveProfile.class);

        assertThat(block.profileId()).isEqualTo("balanced");
        assertThat(block.profileVersion()).isEqualTo("1");
        assertThat(block.policyHash()).isEqualTo("0".repeat(64));
        assertThat(block.definitionHash()).isEqualTo("1".repeat(64));
        assertThat(block.metricRegistryVersion()).isEqualTo("2");
        assertThat(block.generationSettingsHash()).isEqualTo("2".repeat(64));
        assertThat(block.profilesEnabled()).isTrue();
        assertThat(block.searchEnabled()).isTrue();
    }

    @Test
    @SuppressWarnings("unchecked")
    void nothingInTheContractIsLeftUnread() throws IOException {
        Map<String, Object> schema =
                MAPPER.readValue(Files.readString(SCHEMA, StandardCharsets.UTF_8), new TypeReference<>() {});
        Set<String> required = Set.copyOf((java.util.List<String>) schema.get("required"));

        // Round trip through Java and back: a field this record does not carry comes back missing.
        Map<String, Object> written = MAPPER.convertValue(
                MAPPER.convertValue(fixtureBlock(), PythonEffectiveProfile.class),
                new TypeReference<>() {});

        assertThat(written.keySet()).containsAll(required);
        assertThat(written).isEqualTo(fixtureBlock());
    }

    @Test
    void theFixtureCarriesExactlyTheFieldsTheSchemaRequires() throws IOException {
        Map<String, Object> schema =
                MAPPER.readValue(Files.readString(SCHEMA, StandardCharsets.UTF_8), new TypeReference<>() {});
        @SuppressWarnings("unchecked")
        Set<String> properties = ((Map<String, Object>) schema.get("properties")).keySet();

        assertThat(fixtureBlock().keySet()).containsExactlyInAnyOrderElementsOf(properties);
    }

    // --- What a job row says about itself -------------------------------------------------

    private static OptimizationJob job() {
        return new OptimizationJob(new Project("Uravakonda", null), "MULTI_OBJECTIVE_A_STAR",
                "Balanced", new BigDecimal("0.5000"), new BigDecimal("0.5000"),
                new BigDecimal("150.00"), new BigDecimal("33.00"));
    }

    @Test
    void aJobFromBeforeThisContractReportsNoPolicyAtAll() {
        // Every column null. Reporting "profiles were off" here would be a claim the row cannot
        // support - nobody recorded anything either way.
        assertThat(EffectiveProfileResponse.fromEntity(job())).isNull();
    }

    @Test
    void aV0RunWithProfilesOffIsDistinguishableFromOne() {
        OptimizationJob job = job();
        job.applyEffectiveProfile(null, null, null, null, "2", null, false, false);

        EffectiveProfileResponse response = EffectiveProfileResponse.fromEntity(job);

        assertThat(response).isNotNull();
        assertThat(response.profileId()).isNull();
        // False, not null: this run is known to have had profiles off.
        assertThat(response.profilesEnabled()).isFalse();
        assertThat(response.metricRegistryVersion()).isEqualTo("2");
    }

    @Test
    void theRecordedPolicyIsReturnedFieldForField() throws IOException {
        PythonEffectiveProfile block =
                MAPPER.convertValue(fixtureBlock(), PythonEffectiveProfile.class);

        OptimizationJob job = job();
        job.applyEffectiveProfile(block.profileId(), block.profileVersion(), block.policyHash(),
                block.definitionHash(), block.metricRegistryVersion(),
                block.generationSettingsHash(), block.profilesEnabled(), block.searchEnabled());

        EffectiveProfileResponse response = EffectiveProfileResponse.fromEntity(job);

        assertThat(response).isEqualTo(new EffectiveProfileResponse(
                block.profileId(), block.profileVersion(), block.policyHash(),
                block.definitionHash(), block.metricRegistryVersion(),
                block.generationSettingsHash(), block.profilesEnabled(), block.searchEnabled()));
    }

    @Test
    void theRequestedProfileIsRememberedBeforeTheEngineAnswers() {
        // A queued job has been asked for a profile and has no echo yet. It must still know which
        // one, or the choice would not survive the wait for a worker.
        OptimizationJob job = job();
        job.requestProfile("minimum_cost", "1");

        assertThat(job.getProfileId()).isEqualTo("minimum_cost");
        assertThat(job.getProfileVersion()).isEqualTo("1");
        assertThat(job.getProfilesEnabled()).isNull();
    }

    @Test
    void theColumnLengthsHoldTheValuesTheContractDefines() throws IOException {
        // C9 fixes char(64) for the hashes and varchar(16) for the versions. A hash that did not
        // fit would be truncated by the database, and a truncated hash compares unequal forever.
        PythonEffectiveProfile block =
                MAPPER.convertValue(fixtureBlock(), PythonEffectiveProfile.class);

        assertThat(block.policyHash()).hasSize(64);
        assertThat(block.definitionHash()).hasSize(64);
        assertThat(block.generationSettingsHash()).hasSize(64);
        assertThat(block.profileVersion().length()).isLessThanOrEqualTo(16);
        assertThat(block.metricRegistryVersion().length()).isLessThanOrEqualTo(16);
        assertThat(block.profileId().length()).isLessThanOrEqualTo(64);
    }
}
