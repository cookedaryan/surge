package com.power.surge.service;

import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Short-lived store for previewed-but-not-yet-committed imports.
 *
 * <p>Holds the converted FeatureCollection between the {@code /preview} and {@code /commit} calls so
 * the client does not have to re-upload the archive to confirm it. Entries expire after
 * {@link #TTL}; the map is swept on write, which is sufficient for a handful of concurrent imports
 * and avoids introducing a scheduler or a cache dependency.</p>
 */
@Service
public class AssetImportStagingService {

    static final Duration TTL = Duration.ofMinutes(30);

    private final Map<String, StagedImport> staged = new ConcurrentHashMap<>();

    /**
     * @param projectId the project the import was previewed against; re-checked on commit so a
     *                  handle cannot be replayed against a different project
     */
    public record StagedImport(
            UUID projectId,
            String fileName,
            List<Map<String, Object>> features,
            Instant createdAt
    ) {
    }

    public String stage(UUID projectId, String fileName, List<Map<String, Object>> features) {
        evictExpired();
        String importId = "imp-" + UUID.randomUUID();
        staged.put(importId, new StagedImport(projectId, fileName, features, Instant.now()));
        return importId;
    }

    public StagedImport require(UUID projectId, String importId) {
        evictExpired();
        StagedImport entry = staged.get(importId);
        if (entry == null) {
            throw new IllegalArgumentException(
                    "Import '" + importId + "' has expired or does not exist. Upload the file again.");
        }
        if (!entry.projectId().equals(projectId)) {
            throw new IllegalArgumentException("Import '" + importId + "' belongs to a different project.");
        }
        return entry;
    }

    public void discard(String importId) {
        staged.remove(importId);
    }

    private void evictExpired() {
        Instant cutoff = Instant.now().minus(TTL);
        Iterator<Map.Entry<String, StagedImport>> iterator = staged.entrySet().iterator();
        while (iterator.hasNext()) {
            if (iterator.next().getValue().createdAt().isBefore(cutoff)) {
                iterator.remove();
            }
        }
    }
}
