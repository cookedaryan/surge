package com.power.surge.dto.admin;

import com.power.surge.domain.UserRole;

/**
 * A partial update. Both fields are optional: {@code null} means "leave unchanged", so the panel
 * can change a role without touching suspension state and vice versa.
 */
public record UpdateUserRequest(
        UserRole role,
        Boolean enabled
) {
}
