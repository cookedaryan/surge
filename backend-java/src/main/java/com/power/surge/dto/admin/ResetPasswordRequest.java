package com.power.surge.dto.admin;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * An administrator setting a new password directly. There is no email infrastructure behind this
 * deployment, so there is no self-service reset link; the administrator communicates the new
 * password out of band.
 */
public record ResetPasswordRequest(
        @NotBlank @Size(min = 8, max = 128) String newPassword
) {
}
