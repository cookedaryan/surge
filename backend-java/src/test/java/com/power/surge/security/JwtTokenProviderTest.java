package com.power.surge.security;

import com.power.surge.domain.UserRole;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class JwtTokenProviderTest {

    private static final long DAY = 86_400_000L;
    private static final String TEST_SECRET =
            "TEST_SECRET_KEY_FOR_JWT_TOKEN_GENERATION_MUST_BE_AT_LEAST_32_BYTES_LONG";

    private JwtTokenProvider tokenProvider;

    @BeforeEach
    void setUp() {
        tokenProvider = new JwtTokenProvider(TEST_SECRET, DAY);
    }

    @Test
    void generateAndValidateToken_success() {
        UUID userId = UUID.randomUUID();
        String username = "testengineer";
        UserRole role = UserRole.ROLE_ENGINEER;

        String token = tokenProvider.generateToken(userId, username, role);

        assertThat(token).isNotBlank();
        assertThat(tokenProvider.validateToken(token)).isTrue();
        assertThat(tokenProvider.getUsernameFromToken(token)).isEqualTo("testengineer");
        assertThat(tokenProvider.getRoleFromToken(token)).isEqualTo("ROLE_ENGINEER");
    }

    @Test
    void validateToken_failsForInvalidToken() {
        assertThat(tokenProvider.validateToken("invalid.jwt.token")).isFalse();
    }

    @Test
    void exposesWhenTheTokenWasIssued() {
        Instant before = Instant.now().minusSeconds(1);
        String token = tokenProvider.generateToken(UUID.randomUUID(), "someone", UserRole.ROLE_ENGINEER);

        // The authentication filter compares this against the account's last credentials change,
        // so it has to be the real issue time rather than a placeholder.
        assertThat(tokenProvider.getIssuedAtFromToken(token)).isAfterOrEqualTo(before);
    }

    // --- signing key configuration ---------------------------------------
    //
    // The key used to default to a constant written into JwtTokenProvider. The repository is
    // public, so that constant was readable by anyone, and knowing it is enough to mint a token for
    // any user and any role without ever seeing a password. An unconfigured instance looked secure
    // and was wide open, which is why there is now no default at all.

    @Test
    void refusesToStartWithoutASecret() {
        assertThatThrownBy(() -> new JwtTokenProvider("", DAY))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("APP_JWT_SECRET");

        assertThatThrownBy(() -> new JwtTokenProvider(null, DAY))
                .isInstanceOf(IllegalStateException.class);
    }

    @Test
    void refusesTheSecretThatWasCommittedToThePublicRepository() {
        assertThatThrownBy(() -> new JwtTokenProvider(
                "SURGE_SECRET_KEY_FOR_JWT_TOKEN_GENERATION_AND_VALIDATION_32_BYTES_MINIMUM", DAY))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("forge");
    }

    @Test
    void refusesAKeyTooShortToSignSafely() {
        assertThatThrownBy(() -> new JwtTokenProvider("too-short", DAY))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("32 bytes");
    }

    @Test
    void acceptsASufficientlyLongRandomSecret() {
        assertThatCode(() -> new JwtTokenProvider("a-test-signing-key-that-is-at-least-32-bytes-long", DAY))
                .doesNotThrowAnyException();
    }
}
