package com.power.surge.dto.auth;

import com.power.surge.domain.UserRole;

public record AuthResponse(
        String token,
        String username,
        String email,
        UserRole role
) {
}
