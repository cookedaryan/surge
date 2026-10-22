package com.power.surge.service;

import com.power.surge.client.PythonProfileClient;
import com.power.surge.dto.client.python.PythonDefinitionHashResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.client.ResourceAccessException;

import java.io.IOException;
import java.net.ConnectException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNoException;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * WP3-6b: the C7 startup handshake, against an engine serving the published C6 vector.
 *
 * <p>Every case here ends the same way — the service does not start. That is the point of the
 * contract: a Java that cannot confirm which policy the engine is running must not serve ranked
 * results, because a wrong answer would look exactly like a right one.
 */
@ExtendWith(MockitoExtension.class)
class ProfileDefinitionHandshakeTest {

    private static final Path EXPECTED_SHA =
            Path.of("..", "contracts", "profiles", "hash-vector", "expected.sha256");

    @Mock
    private PythonProfileClient profileClient;

    /** The hash the engine would publish if it were running the definitions in the C6 vector. */
    private String vectorHash;

    @BeforeEach
    void readTheVector() throws IOException {
        vectorHash = Files.readString(EXPECTED_SHA, StandardCharsets.UTF_8).strip();
    }

    private ProfileDefinitionHandshake handshake(boolean profilesEnabled, String expectedHash) {
        return new ProfileDefinitionHandshake(profileClient, profilesEnabled, expectedHash);
    }

    private void engineServes(String hash) {
        when(profileClient.definitionHash())
                .thenReturn(new PythonDefinitionHashResponse(hash, "2", "1.0.0"));
    }

    @Test
    void anAgreedHashLetsTheServiceStart() {
        engineServes(vectorHash);

        assertThatNoException().isThrownBy(handshake(true, vectorHash)::afterPropertiesSet);
    }

    @Test
    void aMismatchStopsStartupAndNamesBothHashes() {
        String servedByEngine = "f".repeat(64);
        engineServes(servedByEngine);

        assertThatThrownBy(handshake(true, vectorHash)::afterPropertiesSet)
                .isInstanceOf(IllegalStateException.class)
                // Both values, because the first question an operator asks is which side moved.
                .hasMessageContaining(vectorHash)
                .hasMessageContaining(servedByEngine);
    }

    @Test
    void anUnreachableEngineStopsStartupToo() {
        ResourceAccessException unreachable =
                new ResourceAccessException("Connection refused", new ConnectException("refused"));
        when(profileClient.definitionHash()).thenThrow(unreachable);

        // "Cannot verify" is not "verified". Starting anyway would serve ranked results on an
        // unchecked policy, which is the failure this handshake exists to prevent.
        assertThatThrownBy(handshake(true, vectorHash)::afterPropertiesSet)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("definition-hash")
                .hasCause(unreachable);
    }

    @Test
    void aResponseWithoutAHashStopsStartup() {
        engineServes(null);

        assertThatThrownBy(handshake(true, vectorHash)::afterPropertiesSet)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("no definition_hash");
    }

    @Test
    void aBlankHashIsTreatedAsNoHash() {
        engineServes("   ");

        assertThatThrownBy(handshake(true, vectorHash)::afterPropertiesSet)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("no definition_hash");
    }

    @Test
    void enablingProfilesWithoutAnExpectedHashStopsStartupBeforeAnyCall() {
        // FRZ-1 sets the expected hash. Before it, enabling profiles is not a configuration that
        // can be verified, so it is refused rather than allowed through unchecked.
        assertThatThrownBy(handshake(true, "")::afterPropertiesSet)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("expected-definition-hash")
                .hasMessageContaining("FRZ-1");

        verifyNoInteractions(profileClient);
    }

    @Test
    void anUnsetExpectedHashIsTheSameAsABlankOne() {
        assertThatThrownBy(handshake(true, null)::afterPropertiesSet)
                .isInstanceOf(IllegalStateException.class);

        verifyNoInteractions(profileClient);
    }

    @Test
    void profilesOffMeansNoHandshakeAtAll() {
        // C7 puts the condition on Java's side, and profiles default off, so today every
        // deployment takes this path. It must not depend on the engine being reachable, or a
        // V0-only service could not start without one.
        assertThatNoException().isThrownBy(handshake(false, "")::afterPropertiesSet);

        verifyNoInteractions(profileClient);
    }

    @Test
    void profilesOffIgnoresEvenAHashThatWouldNotMatch() {
        assertThatNoException()
                .isThrownBy(handshake(false, "not-a-hash-anyone-published")::afterPropertiesSet);

        verifyNoInteractions(profileClient);
    }

    @Test
    void theVectorHashIsTheShapeTheHandshakeCompares() {
        // Guards the fixture this test reads: a truncated or re-wrapped expected.sha256 would make
        // every case above pass against a value that is not a hash.
        assertThat(vectorHash).matches("[0-9a-f]{64}");
    }
}
