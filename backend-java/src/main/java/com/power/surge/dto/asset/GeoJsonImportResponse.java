package com.power.surge.dto.asset;

import java.util.List;
import java.util.UUID;

public record GeoJsonImportResponse(
        UUID projectId,
        int wtgsImported,
        int substationsImported,
        int totalImported,
        List<WtgResponse> wtgs,
        List<SubstationResponse> substations
) {
}
