package com.power.surge.dto.asset;

import jakarta.validation.constraints.NotBlank;

import java.math.BigDecimal;
import java.util.Map;

/**
 * Confirms a previewed import.
 *
 * @param importId          handle returned by the preview call
 * @param overrides         external ID to {@link com.power.surge.domain.AssetType} name, applied
 *                          before persistence so the user can correct any misdetection
 * @param statusOverrides   external ID to {@link com.power.surge.domain.WtgStatus} name
 * @param defaultCapacityMw capacity applied to turbines whose source carries none. Survey KMZ files
 *                          have no ExtendedData at all, so this is the only place a real capacity
 *                          can come from.
 * @param skipUnclassified  when false, the request is rejected if any feature is still UNKNOWN
 */
public record CommitAssetImportRequest(
        @NotBlank String importId,
        Map<String, String> overrides,
        Map<String, String> statusOverrides,
        BigDecimal defaultCapacityMw,
        Boolean skipUnclassified
) {

    public Map<String, String> overridesOrEmpty() {
        return overrides == null ? Map.of() : overrides;
    }

    public Map<String, String> statusOverridesOrEmpty() {
        return statusOverrides == null ? Map.of() : statusOverrides;
    }

    public boolean skipUnclassifiedOrDefault() {
        return skipUnclassified == null || skipUnclassified;
    }
}
