package com.power.surge.security;

import com.power.surge.domain.UserRole;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.UUID;

@Component
public class JwtTokenProvider {

    /** The key this class used to default to. Burned — it is in the public git history. */
    static final String PUBLISHED_PLACEHOLDER = "SURGE_SECRET_KEY_FOR_JWT_TOKEN_GENERATION";

    private final SecretKey key;
    private final long expirationMs;

    /**
     * The signing key has no default on purpose.
     *
     * <p>It used to fall back to a constant written in this file. Because the repository is public,
     * that constant was readable by anyone, and knowing it is enough to mint a token for any user
     * and any role without ever seeing a password — no login, no lockout, nothing to notice. An
     * instance that was never explicitly configured looked perfectly secure while being wide open.
     *
     * <p>Refusing to start is the only safe behaviour: a service that will not boot gets fixed,
     * whereas one that silently signs with a published key does not.
     */
    public JwtTokenProvider(
            @Value("${app.jwt.secret:}") String secret,
            @Value("${app.jwt.expiration-ms:86400000}") long expirationMs
    ) {
        if (secret == null || secret.isBlank()) {
            throw new IllegalStateException(
                    "app.jwt.secret is not set. Generate a random value (at least 32 bytes) and supply it "
                            + "via the APP_JWT_SECRET environment variable. There is deliberately no default.");
        }
        if (secret.getBytes(StandardCharsets.UTF_8).length < 32) {
            throw new IllegalStateException(
                    "app.jwt.secret must be at least 32 bytes for HMAC-SHA signing; got "
                            + secret.getBytes(StandardCharsets.UTF_8).length + " bytes.");
        }
        if (secret.startsWith(PUBLISHED_PLACEHOLDER)) {
            throw new IllegalStateException(
                    "app.jwt.secret is set to the placeholder that was previously committed to this "
                            + "repository. It is public and anyone can forge tokens with it. Generate a new "
                            + "random value.");
        }
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.expirationMs = expirationMs;
    }

    public String generateToken(UUID userId, String username, UserRole role) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + expirationMs);

        return Jwts.builder()
                .subject(username)
                .claim("userId", userId.toString())
                .claim("role", role.name())
                .issuedAt(now)
                .expiration(expiryDate)
                .signWith(key)
                .compact();
    }

    public String getUsernameFromToken(String token) {
        return getClaims(token).getSubject();
    }

    public String getRoleFromToken(String token) {
        return getClaims(token).get("role", String.class);
    }

    /** When this token was minted, used to reject tokens older than a credentials change. */
    public Instant getIssuedAtFromToken(String token) {
        Date issuedAt = getClaims(token).getIssuedAt();
        return issuedAt != null ? issuedAt.toInstant() : Instant.EPOCH;
    }

    public boolean validateToken(String token) {
        try {
            getClaims(token);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private Claims getClaims(String token) {
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}
