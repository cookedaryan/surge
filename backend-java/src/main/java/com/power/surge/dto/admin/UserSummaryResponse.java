package com.power.surge.dto.admin;

import com.power.surge.domain.User;
import com.power.surge.domain.UserRole;

import java.time.Instant;
import java.util.UUID;

/**
 * An account as shown in the admin panel. Deliberately carries no password material of any kind,
 * not even the hash.
 */
public record UserSummaryResponse(
        UUID id,
        String username,
        String email,
        UserRole role,
        boolean enabled,
        Instant createdAt
) {
    public static UserSummaryResponse fromEntity(User user) {
        return new UserSummaryResponse(
                user.getId(),
                user.getUsername(),
                user.getEmail(),
                user.getRole(),
                user.isEnabled(),
                user.getCreatedAt()
        );
    }
}
