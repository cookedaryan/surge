package com.power.surge.dto.asset;

import java.util.List;
import java.util.UUID;

public record ProjectAssetsResponse(
        UUID projectId,
        int totalWtgs,
        int totalSubstations,
        List<WtgResponse> wtgs,
        List<SubstationResponse> substations
) {
}
