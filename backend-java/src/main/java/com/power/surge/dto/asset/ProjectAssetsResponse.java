package com.power.surge.dto.asset;

import java.util.List;
import java.util.UUID;

public record ProjectAssetsResponse(
        UUID projectId,
        int totalWtgs,
        int totalOptimisableWtgs,
        int totalSubstations,
        int totalTowers,
        List<WtgResponse> wtgs,
        List<SubstationResponse> substations,
        List<EvacuationTowerResponse> towers
) {
}
