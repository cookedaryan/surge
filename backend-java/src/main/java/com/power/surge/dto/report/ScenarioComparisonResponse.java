package com.power.surge.dto.report;

import java.util.List;
import java.util.UUID;

public record ScenarioComparisonResponse(
        UUID projectId,
        List<ScenarioSummaryItem> scenarios
) {
}
