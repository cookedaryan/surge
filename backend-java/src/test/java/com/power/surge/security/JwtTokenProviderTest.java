package com.power.surge.security;

import com.power.surge.domain.UserRole;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class JwtTokenProviderTest {

    private JwtTokenProvider tokenProvider;

    @BeforeEach
    void setUp() {
        tokenProvider = new JwtTokenProvider(
                "TEST_SECRET_KEY_FOR_JWT_TOKEN_GENERATION_MUST_BE_AT_LEAST_32_BYTES_LONG",
                86400000L
        );
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
}
