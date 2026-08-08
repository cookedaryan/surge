package com.power.surge.dto.project;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CreateProjectRequest(
        @NotBlank(message = "Project name is required.")
        @Size(max = 200, message = "Project name must not exceed 200 characters.")
        String name,
        String description
) {
}
