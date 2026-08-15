package com.power.surge.dto.admin;

import com.power.surge.domain.UserRole;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/** An administrator provisioning an account for a colleague. */
public record CreateUserRequest(
        @NotBlank @Size(min = 3, max = 64) String username,
        @NotBlank @Email @Size(max = 128) String email,
        @NotBlank @Size(min = 8, max = 128) String password,
        @NotNull UserRole role
) {
}
