package com.power.surge.service;

import java.util.UUID;

public class ProjectNotFoundException extends RuntimeException {

    public ProjectNotFoundException(UUID projectId) {
        super("Project " + projectId + " was not found.");
    }
}
